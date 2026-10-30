"""Build a narrated slideshow demo video (offline data): PIL slides + TTS voice + ffmpeg.

Usage: python3 scripts/make_demo_video.py [--today 2026-11-01]  -> data/demo/paypal_counsel_demo.mp4
Every number on screen and in the narration comes from running this repo's CLI on the synthetic
fixtures (seed --source mock, queue, deadlines, packet, dashboard) in a scratch directory, so the
repo's own data/ files are not touched. Voice: edge-tts if it works, else espeak-ng. Needs ffmpeg.
The dashboard slide is a headless Chrome screenshot when Chrome is on PATH.
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from counsel.queue import DEFAULT_FEE  # noqa: E402

OUT = ROOT / "data" / "demo"
W, H = 1280, 720
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FOOTER = "Chargeback Counsel for PayPal  |  SYNTHETIC sandbox fixtures, not real disputes or buyers"
VOICE = "en-US-GuyNeural"
APPROVER = "Demo Merchant"
MAX_SECONDS = 180


def cli(work: pathlib.Path, *args: str) -> str:
    """Run `python3 -m counsel.<args>` in the scratch dir and return stdout."""
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-m", *args], cwd=work, env=env, check=True, capture_output=True, text=True)
    return r.stdout.rstrip("\n")


def short(dispute_id: str) -> str:
    """Speakable form: PP-D-SYNTH-0003 -> 'synthetic dispute 3'."""
    return f"synthetic dispute {int(dispute_id.rsplit('-', 1)[-1])}"


def words(text: str) -> str:
    return text.replace("_", " ")


def slide(path, title, body, mono=True, image=None):
    img = Image.new("RGB", (W, H), (12, 22, 44))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=(0, 112, 224))
    d.text((48, 32), title, font=ImageFont.truetype(SANS, 38), fill=(255, 255, 255))
    y = 104
    if image is not None:
        shot = Image.open(image).convert("RGB")
        shot.thumbnail((W - 96, H - y - 60))
        img.paste(shot, ((W - shot.width) // 2, y))
    f = ImageFont.truetype(MONO if mono else SANS, 17 if mono else 28)
    lines = []
    for raw in (l for chunk in body for l in chunk.split("\n")):
        while len(raw) > 104:  # wrap long lines (e.g. commands) instead of cutting them off
            cut = raw.rfind(" ", 0, 104)
            cut = cut if cut > 0 else 104
            lines.append(raw[:cut])
            raw = ("    " if not raw.startswith("    ") else "") + raw[cut:].lstrip()
        lines.append(raw)
    for line in lines:
        color = (210, 220, 235)
        if line.startswith("$ "):
            color = (120, 200, 255)
        elif "urgent" in line or "missed" in line:
            color = (255, 170, 110)
        d.text((48, y), line, font=f, fill=color)
        y += 23 if mono else 46
    d.rectangle([0, H - 44, W, H], fill=(30, 36, 52))
    d.text((48, H - 34), FOOTER, font=ImageFont.truetype(MONO, 16), fill=(255, 200, 90))
    img.save(path)


def screenshot(html_path: pathlib.Path, png: pathlib.Path) -> bool:
    chrome = next((shutil.which(c) for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
    if not chrome:
        return False
    r = subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1600,900", f"--screenshot={png}", html_path.as_uri()], capture_output=True)
    if r.returncode != 0 or not png.exists():
        return False
    shot = Image.open(png).convert("RGB")
    box = Image.eval(shot, lambda v: 255 - v).getbbox()  # trim white margins around the page content
    if box:
        l, t, rr, b = box
        shot.crop((max(l - 16, 0), max(t - 16, 0), min(rr + 16, shot.width), min(b + 16, shot.height))).save(png)
    return True


def speak(text: str, base: pathlib.Path) -> pathlib.Path:
    if shutil.which("edge-tts"):
        mp3 = base.with_suffix(".mp3")
        r = subprocess.run(["edge-tts", "--voice", VOICE, "--rate=+5%", "--text", text, "--write-media", str(mp3)],
                           capture_output=True)
        if r.returncode == 0 and mp3.exists() and mp3.stat().st_size > 0:
            return mp3
    if shutil.which("espeak-ng"):
        wav = base.with_suffix(".wav")
        subprocess.run(["espeak-ng", "-v", "en-us", "-s", "155", "-w", str(wav), text], check=True)
        return wav
    sys.exit("error: no working TTS (edge-tts or espeak-ng)")


def duration(path: pathlib.Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


def test_count() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT,
                       capture_output=True, text=True)
    m = re.search(r"(\d+) passed", r.stdout)
    if r.returncode != 0 or not m:
        sys.exit("error: test suite failed; not rendering a video that claims tests pass\n" + r.stdout[-2000:])
    return int(m.group(1))


def build_slides(work: pathlib.Path, today: str, tests: int) -> list[tuple]:
    seed_cmd = ("counsel.seed", "--source", "mock")
    seed_out = cli(work, *seed_cmd)
    fixtures = json.loads((ROOT / "data" / "mock_paypal_disputes.json").read_text())["items"]
    queue_out = cli(work, "counsel.queue")
    queue = json.loads(cli(work, "counsel.queue", "--json"))
    deadlines_out = cli(work, "counsel.deadlines", "--today", today)
    cli(work, "counsel.packet", "--json")
    packets = {p.stem: json.loads(p.read_text()) for p in (work / "data" / "packets").glob("*.json")}
    cli(work, "counsel.packet")

    fee = DEFAULT_FEE  # the queue CLI above ran with its default handling cost
    contest = [q for q in queue if q["action"] == "contest"]
    accept = [q for q in queue if q["action"] == "accept"]
    # Show the "item not received" packet if there is one (the PayPal storyboard case), else the top contest item.
    pick = next((q["id"] for q in contest if packets[q["id"]]["reason"] == "product_not_received"), contest[0]["id"])
    pk = packets[pick]
    packet_md = (work / "data" / "packets" / f"{pick}.md").read_text().splitlines()

    approve_cmd = ("counsel.dashboard", "--today", today, "--approve", pick, "--action", "provide_evidence",
                   "--approver", APPROVER)
    approve_out = cli(work, *approve_cmd)
    approvals = (work / "data" / "approvals.json").read_text().rstrip().splitlines()
    shot = work / "dashboard.png"
    has_shot = screenshot(work / "data" / "dashboard.html", shot)

    urgent = re.findall(r"\| (\S+) \| (-?\d+) \| (urgent|missed) \|", deadlines_out)
    reason_by_id = {f["dispute_id"]: f["reason"] for f in fixtures}
    ev_total = round(sum(q["ev"] for q in contest), 2)
    currencies = {p["currency"] for p in packets.values()}
    cur = currencies.pop() if len(currencies) == 1 else ""
    gap = pk["evidence_missing"][0] if pk["evidence_missing"] else None

    fixture_rows = [f"{f['dispute_id']:<17}{f['reason']:<42}{f['dispute_amount']['value']:>8} "
                    f"{f['dispute_amount']['currency_code']}  due {f['seller_response_due_date'][:10]}" for f in fixtures]
    packet_body = [l for l in packet_md if l.strip() and not l.startswith("- [ ]")][:20]

    def cmd(args):
        return "$ python3 -m " + " ".join(f'"{a}"' if " " in a else a for a in args)

    s = []
    s.append(("Chargeback Counsel for PayPal",
              ["Works a merchant's PayPal dispute queue.", "Ranks disputes, watches evidence deadlines,",
               "and drafts responses. A person approves every action.", "",
               "All data in this video: synthetic fixtures shaped", "like PayPal sandbox responses. No real buyers."], False,
              "This is Chargeback Counsel for PayPal. It ranks a merchant's PayPal disputes, watches evidence "
              "deadlines and drafts responses, and a person approves every action. "
              "All data shown is synthetic, shaped like PayPal sandbox responses."))
    s.append(("The problem",
              ["Small merchants lose disputes they could win.", "A missed evidence deadline is an automatic loss.",
               "The merchant loses the amount plus the fee."], False,
              "Small merchants lose disputes they could win because the evidence is late. "
              "A missed deadline loses the amount plus the fee."))
    s.append(("1. Load disputes (offline fixtures)",
              [cmd(seed_cmd), seed_out, "", "Fixture: data/mock_paypal_disputes.json (PayPal Disputes API shape)", ""]
              + fixture_rows, True,
              f"The seed command loads {len(fixtures)} synthetic disputes in the PayPal Disputes API shape and maps "
              "each PayPal reason code to a playbook. The live source paypal option is written but not yet run "
              "against the sandbox."))
    s.append(("2. Triage queue: contest or accept",
              [cmd(("counsel.queue",)), ""] + queue_out.splitlines(), True,
              "The queue scores each dispute from its reason code playbook and the evidence on hand. "
              f"Expected value is win probability times amount, minus a {fee:g} dollar handling cost. It recommends contesting {len(contest)} and accepting {len(accept)}. "
              + " ".join(f"{short(q['id']).capitalize()} scores {q['p_win']:.2f}, so contesting it would lose money."
                         for q in accept)))
    s.append(("3. Deadlines first",
              [cmd(("counsel.deadlines", "--today", today)), ""] + deadlines_out.splitlines(), True,
              f"As of {today}, {len(urgent)} disputes worth contesting are due within three days: "
              + ", and ".join(f"{short(i)}, {words(reason_by_id[i]).lower()}, with {n} days left" for i, n, _ in urgent)
              + "."))
    s.append((f"4. Evidence packet: {pick}",
              [cmd(("counsel.packet",)) + f"   ->  data/packets/{pick}.md", ""] + packet_body, True,
              f"Each dispute gets an evidence packet. For {short(pick)}, {words(reason_by_id[pick]).lower()}, "
              f"it has {' and '.join(words(k) for k in pk['evidence_on_hand']) or 'no evidence'} on hand. "
              + (f"Missing: {words(gap['field'])}, worth {gap['gain']:.2f} more win probability. " if gap else "")
              + "The draft comes from a reason code template for now, and starts unapproved."))
    s.append(("5. Approval gate",
              [cmd(approve_cmd), approve_out, "", "data/approvals.json:"] + approvals
              + ["", "PayPalClient.provide_evidence / accept_claim call approval.require()",
                 "and raise NotApproved without a matching record."], True,
              "Approval is a separate step. This command records who approved which action on which dispute, "
              "and does not call PayPal. The client's submit methods refuse to run without a matching record."))
    if has_shot:
        s.append(("6. Approval dashboard (data/dashboard.html)", [], True,
                  "The static dashboard shows the same queue with deadlines, expected value, evidence gaps and "
                  f"approval status. {short(pick).capitalize()} now shows approved. The page cannot submit anything.", shot))
    s.append(("Where this stands",
              [f"Expected net recovery, {len(contest)} contested disputes: {ev_total:.2f} {cur}".rstrip(),
               "  (sum of the EV column above; synthetic fixtures)",
               f"Test suite: {tests} passed", "",
               "Not done yet:",
               "  - run --source paypal against the PayPal sandbox",
               "  - submit approved evidence to the sandbox",
               "  - webhook ingest and language model drafting", "",
               "MIT licensed."], True,
              f"On this synthetic queue, the expected net recovery across the {len(contest)} contested disputes is "
              f"{ev_total:.2f} {'dollars' if cur == 'USD' else cur}. {tests} tests pass. Next: run against the "
              "PayPal sandbox, submit approved evidence there, and add webhooks and model drafting. MIT licensed."))
    return s


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--today", default=os.environ.get("TODAY", "2026-11-01"), help="date for deadline math")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    tests = test_count()
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        slides = build_slides(work, a.today, tests)
        parts = []
        for i, (t, body, mono, say, *img) in enumerate(slides):
            png, mp4 = work / f"s{i}.png", work / f"s{i}.mp4"
            slide(png, t, body, mono, img[0] if img else None)
            audio = speak(say, work / f"s{i}")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(audio),
                            "-af", "apad=pad_dur=0.7", "-ar", "44100", "-ac", "1", "-c:v", "libx264", "-tune", "stillimage",
                            "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-shortest", str(mp4)], check=True)
            parts.append(mp4)
        lst = work / "parts.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        final = OUT / "paypal_counsel_demo.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", str(final)], check=True)
    secs = duration(final)
    print(f"wrote {final.relative_to(ROOT)} ({secs:.1f} s, {len(slides)} slides, {tests} tests passed)")
    if secs > MAX_SECONDS:
        sys.exit(f"error: video is {secs:.1f} s, over the {MAX_SECONDS} s limit")


if __name__ == "__main__":
    main()
