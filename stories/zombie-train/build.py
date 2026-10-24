#!/usr/bin/env python3
"""Озвучка, субтитры и аниматик для «Зомби-апокалипсис в поезде».

Использование:
    python3 build.py /path/to/ru-irinia-medium.onnx

Создаёт в папке out/: voiceover.mp3, subtitles.srt, subtitles.ass,
timeline.txt и animatic.mp4 (1080x1920, голос + звуковой фон + субтитры).
"""
import os
import subprocess
import sys
import wave

import numpy as np
from piper import PiperVoice, SynthesisConfig

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SR = 22050

# (сцена, текст диктора, пауза после реплики в секундах, эффект)
# эффект: None — голос диктора, "radio" — голос из рации/динамика
CUES = [
    (1, "Если зомби-апокалипсис начнётся, пока ты в ночном поезде,", 0.1, None),
    (1, "у тебя будет меньше минуты.", 0.4, None),

    (2, "Три часа ночи. Второй вагон.", 0.2, None),
    (2, "Купе спит. Стук колёс убаюкивает.", 0.5, None),

    (3, "И вдруг — удар.", 0.15, None),
    (3, "Поезд встаёт посреди ничего.", 0.4, None),

    (4, "Ни станции. Ни фонарей. Только чёрный лес.", 0.2, None),
    (4, "А из третьего вагона — глухой удар в стену. Ещё один.", 0.4, None),

    (5, "Проводница жмёт кнопку связи.", 0.1, None),
    (5, "Кабина, ответьте! Кабина!", 0.2, "radio"),
    (5, "Шипение. Машинист молчит.", 0.4, None),

    (6, "И тут все телефоны вибрируют разом.", 0.15, None),
    (6, "Неизвестная инфекция. Оставайтесь на месте.", 0.3, "radio"),
    (6, "За дверью третьего вагона — крик.", 0.4, None),

    (7, "Люди срываются и бегут вперёд.", 0.1, None),
    (7, "Ты хочешь за ними. Не беги.", 0.2, None),
    (7, "Коридор — шириной в одно плечо.", 0.1, None),
    (7, "Толпа — это давка и тупик, которого ты не видишь.", 0.15, None),
    (7, "Ты отступаешь в купе и пропускаешь их.", 0.4, None),

    (8, "Дыши. Считай.", 0.2, None),
    (8, "Два тамбура. Аварийное окно. Замок на двери купе.", 0.2, None),
    (8, "Впереди толпа открывает тамбур и прыгает в темноту.", 0.1, None),
    (8, "А ты не видишь, кто ждёт их внизу.", 0.4, None),

    (9, "Лампы мигают.", 0.2, None),
    (9, "Раз. Два.", 0.3, None),
    (9, "Темнота.", 0.4, None),
    (9, "Вентиляция стихает. Ты слышишь своё дыхание.", 0.15, None),
    (9, "Не включай фонарик. Ночью свет видно за километр.", 0.4, None),

    (10, "Проводница щёлкает рацией.", 0.1, None),
    (10, "Машинист, приём! Машинист!", 0.2, "radio"),
    (10, "Щелчок. Кто-то нажал кнопку… и промолчал.", 0.4, None),

    (11, "Стоящий поезд — железный коридор с двумя выходами.", 0.1, None),
    (11, "Единственный свет на десятки километров.", 0.1, None),
    (11, "И всё, что бродит в этом лесу, уже идёт к нему.", 0.4, None),

    (12, "Назад — третий вагон. Вниз — темнота.", 0.2, None),
    (12, "Вперёд — кабина. Стальная дверь и тормоз.", 0.3, None),
    (12, "Ты выбираешь — вперёд.", 0.4, None),

    (13, "Первый вагон пуст.", 0.1, None),
    (13, "На полу светится чей-то телефон.", 0.1, None),
    (13, "Последний тамбур. Ветер между вагонами.", 0.4, None),

    (14, "Дверь кабины приоткрыта.", 0.4, None),
    (14, "Внутри никого.", 0.4, None),
    (14, "Только красная лампа на пульте.", 0.4, None),

    (15, "И вдруг пол вздрагивает.", 0.2, None),
    (15, "Поезд трогается. Сам.", 0.4, None),
    (15, "Прожектор выхватывает другой поезд впереди.", 0.5, None),

    (16, "Все окна тёмные. Кроме одного.", 0.3, None),
    (16, "Там человек. Он бьёт по стеклу и показывает тебе:", 0.2, None),
    (16, "не останавливайся.", 1.1, None),

    (17, "Но кто тогда управляет твоим поездом?", 1.9, None),
]

SCENE_TITLES = {
    1: "Крючок", 2: "Ночной поезд", 3: "Экстренное торможение",
    4: "Первые секунды", 5: "Связь с машинистом", 6: "Оповещение",
    7: "Не беги с толпой", 8: "Оценка обстановки", 9: "Отключение света",
    10: "Рация", 11: "Ловушка", 12: "Решение", 13: "Путь вперёд",
    14: "Кабина машиниста", 15: "Поезд трогается", 16: "Человек в окне",
    17: "Финал",
}


def synth(voice, text, length_scale):
    path = os.path.join(OUT, "_tmp.wav")
    cfg = SynthesisConfig(length_scale=length_scale, noise_scale=0.6, noise_w_scale=0.7)
    with wave.open(path, "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=cfg)
    with wave.open(path, "rb") as wf:
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    os.remove(path)
    audio = data.astype(np.float32) / 32768.0
    # обрезаем тишину по краям, чтобы паузы задавались только сценарием
    idx = np.where(np.abs(audio) > 0.01)[0]
    if len(idx):
        audio = audio[max(idx[0] - 200, 0): idx[-1] + 600]
    return audio


def onepole_lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def radio(x):
    # узкая полоса + лёгкий перегруз: голос из динамика/рации
    hp = x - onepole_lowpass(x, 350)
    bp = onepole_lowpass(hp, 3200)
    bp = np.tanh(bp * 4.0) / 2.2
    return bp + np.random.randn(len(bp)).astype(np.float32) * 0.006


def fmt_srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def fmt_ass(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def build_bed(total, scene_start, scene_end):
    """Звуковой фон аниматика: гул, стук колёс, тормоза, удары, вибрация, сердце."""
    rng = np.random.default_rng(7)
    n = int(round(total * SR))
    t = np.arange(n) / SR
    bed = np.zeros(n, dtype=np.float32)

    def span(a, b):
        return int(a * SR), min(int(b * SR), n)

    def burst(at, dur, freq, gain, noise=0.0, decay=8.0):
        i0, i1 = span(at, at + dur)
        tt = np.arange(i1 - i0) / SR
        env = np.exp(-decay * tt)
        sig = np.sin(2 * np.pi * freq * tt) + noise * rng.standard_normal(len(tt))
        bed[i0:i1] += (gain * env * sig).astype(np.float32)

    # гул поезда: коричневый шум
    brown = np.cumsum(rng.standard_normal(n)).astype(np.float32)
    brown -= onepole_lowpass(brown, 0.5)
    brown /= np.max(np.abs(brown)) + 1e-9
    env = np.zeros(n, dtype=np.float32)
    move_end = scene_start[3] + 1.2
    a, b = span(0, move_end)
    env[a:b] = 0.5
    a, b = span(move_end, move_end + 2.0)
    env[a:b] = np.linspace(0.5, 0.06, b - a)
    a, b = span(move_end + 2.0, scene_start[9] + 2.0)
    env[a:b] = 0.06  # стоящий поезд: только вентиляция
    a, b = span(scene_start[15] + 1.0, scene_end[16])
    env[a:b] = np.linspace(0.05, 0.45, b - a)
    bed += brown * env

    # стук колёс «та-дам» в движении и после самостоятельного старта
    def clacks(t0, t1, period):
        x = t0
        while x < t1:
            burst(x, 0.12, 90, 0.25, noise=0.6, decay=40)
            burst(x + 0.18, 0.12, 80, 0.22, noise=0.6, decay=40)
            x += period
    clacks(0.3, scene_start[3], 1.4)
    clacks(scene_start[15] + 1.5, scene_end[16], 2.4)

    # визг тормозов
    i0, i1 = span(scene_start[3], scene_start[3] + 2.2)
    tt = np.arange(i1 - i0) / SR
    screech = np.sin(2 * np.pi * (2600 - 500 * tt) * tt) * np.exp(-1.2 * tt)
    bed[i0:i1] += (0.12 * screech).astype(np.float32)
    burst(scene_start[3] + 0.1, 0.5, 45, 0.6, noise=0.3, decay=6)

    # глухие удары из третьего вагона
    for k in range(3):
        burst(scene_start[4] + 3.2 + k * 0.9, 0.4, 55, 0.5, noise=0.2, decay=10)

    # вибрация телефонов
    for k in range(3):
        a0 = scene_start[6] + 1.0 + k * 0.6
        i0, i1 = span(a0, a0 + 0.35)
        tt = np.arange(i1 - i0) / SR
        bed[i0:i1] += (0.1 * np.sign(np.sin(2 * np.pi * 170 * tt))).astype(np.float32)

    # гудение ламп, обрывающееся при отключении света
    a, b = span(move_end, scene_start[9] + 2.0)
    hum = 0.03 * np.sin(2 * np.pi * 100 * t[a:b])
    flick = (rng.random(b - a) > 0.0).astype(np.float32)
    for c in (0.3, 0.9, 1.5):
        fa, fb = span(scene_start[9] + c, scene_start[9] + c + 0.12)
        flick[fa - a:fb - a] = 0
    bed[a:b] += (hum * flick).astype(np.float32)

    # сердцебиение от «ловушки» до кабины
    x = scene_start[11]
    while x < scene_start[15]:
        burst(x, 0.15, 50, 0.35, decay=25)
        burst(x + 0.22, 0.15, 45, 0.25, decay=25)
        x += 0.95

    # финальный удар при затемнении
    burst(scene_start[17] - 0.2, 3.0, 35, 0.8, noise=0.15, decay=1.5)
    a, b = span(scene_start[17] - 0.2, total)
    bed[a:b] *= np.linspace(1, 0, b - a) ** 0.5
    return bed


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    os.makedirs(OUT, exist_ok=True)
    voice = PiperVoice.load(sys.argv[1])

    parts, timeline = [], []
    cursor = 0.3  # короткая тишина перед первой фразой
    parts.append(np.zeros(int(cursor * SR), dtype=np.float32))
    for scene, text, pause, fx in CUES:
        spoken = text.replace(" — ", " ")
        audio = synth(voice, spoken, 0.77)
        if fx == "radio":
            audio = radio(audio)
        start, end = cursor, cursor + len(audio) / SR
        timeline.append((scene, text, start, end))
        parts += [audio, np.zeros(int(pause * SR), dtype=np.float32)]
        cursor = end + pause
    voice_track = np.concatenate(parts)
    total = len(voice_track) / SR

    # субтитр держится чуть дольше фразы, но не наезжает на следующий
    sub_end = [min(e + 0.15, timeline[i + 1][2] - 0.02) if i + 1 < len(timeline) else e + 0.15
               for i, (_, _, _, e) in enumerate(timeline)]

    scene_start, scene_end = {}, {}
    for scene, _, s, e in timeline:
        scene_start.setdefault(scene, s)
        scene_end[scene] = e
    # сцена начинается чуть раньше своей первой фразы
    for sc in scene_start:
        scene_start[sc] = max(scene_start[sc] - 0.3, 0)
    scene_start[1] = 0.0
    scene_end[17] = total

    voice_track /= np.max(np.abs(voice_track)) + 1e-9
    bed = build_bed(total, scene_start, scene_end)
    mix = 0.9 * voice_track + 0.35 * bed
    mix /= np.max(np.abs(mix)) + 1e-9

    def write_wav(path, x):
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes((np.clip(x, -1, 1) * 32767 * 0.95).astype(np.int16).tobytes())

    write_wav(os.path.join(OUT, "_voice.wav"), voice_track)
    write_wav(os.path.join(OUT, "_mix.wav"), mix)
    # лёгкая «комната» и громкость под TikTok (-14 LUFS)
    af = "aecho=0.8:0.5:40:0.12,loudnorm=I=-14:TP=-1.5:LRA=11"
    for src, dst in (("_voice.wav", "voiceover.mp3"), ("_mix.wav", "voiceover_with_sfx.mp3")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(OUT, src),
                        "-af", af, "-ar", "44100", "-b:a", "192k", os.path.join(OUT, dst)], check=True)

    # субтитры: SRT для загрузки в TikTok/CapCut, ASS со стилем для вшивания
    with open(os.path.join(OUT, "subtitles.srt"), "w", encoding="utf-8") as f:
        for i, ((_, text, s, _), e) in enumerate(zip(timeline, sub_end), 1):
            sub = text.upper() if text == "не останавливайся." else text
            f.write(f"{i}\n{fmt_srt(s)} --> {fmt_srt(e)}\n{sub}\n\n")

    ass = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Main,DejaVu Sans,62,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,0,0,1,5,2,2,90,90,560,1",
        "Style: Radio,DejaVu Sans,58,&H0080E0FF,&H000000FF,&H00000000,&H64000000,"
        "-1,-1,0,0,100,100,0,0,1,5,2,2,90,90,560,1",
        "Style: Shout,DejaVu Sans,96,&H002020FF,&H000000FF,&H00000000,&H64000000,"
        "-1,0,0,0,100,100,2,0,1,6,3,5,60,60,0,1",
        "Style: Final,DejaVu Serif,70,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "0,-1,0,0,100,100,1,0,1,0,0,5,90,90,0,1",
        "Style: Scene,DejaVu Sans,30,&H00B0B0B0,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,4,0,1,0,0,8,60,60,140,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    fx_by_text = {text: fx for _, text, _, fx in CUES}
    for (_, text, s, _), e in zip(timeline, sub_end):
        if text == "не останавливайся.":
            style, body = "Shout", r"{\fad(80,0)}НЕ ОСТАНАВЛИВАЙСЯ"
        elif text.startswith("Но кто тогда"):
            style, body = "Final", r"{\fad(600,0)}Но кто тогда управляет\Nтвоим поездом?.."
            e = total - 0.05
        else:
            style = "Radio" if fx_by_text[text] == "radio" else "Main"
            body = r"{\fad(120,80)}" + text
        ass.append(f"Dialogue: 0,{fmt_ass(s)},{fmt_ass(e)},{style},,0,0,0,,{body}")
    for sc, st in scene_start.items():
        ass.append(f"Dialogue: 1,{fmt_ass(st)},{fmt_ass(scene_end[sc] + 0.2)},Scene,,0,0,0,,"
                   f"СЦЕНА {sc} · {SCENE_TITLES[sc].upper()}")
    ass.append(f"Dialogue: 0,{fmt_ass(total - 1.6)},{fmt_ass(total)},Scene,,0,0,0,,"
               r"{\an2\fs44\c&H00FFFFFF&\fad(300,0)}ПРОДОЛЖЕНИЕ СЛЕДУЕТ")
    with open(os.path.join(OUT, "subtitles.ass"), "w", encoding="utf-8") as f:
        f.write("\n".join(ass) + "\n")

    with open(os.path.join(OUT, "timeline.txt"), "w", encoding="utf-8") as f:
        for sc in sorted(scene_start):
            f.write(f"Сцена {sc:2} {SCENE_TITLES[sc]:24} {fmt_srt(scene_start[sc])[3:-4]}"
                    f" – {fmt_srt(scene_end[sc] + 0.2)[3:-4]}\n")
        f.write(f"Итого: {total:.1f} с\n")

    # аниматик: тёмный фон, голос, звуковой фон, вшитые субтитры
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=0x07090c:s=1080x1920:r=30:d={total:.2f}",
        "-i", os.path.join(OUT, "voiceover_with_sfx.mp3"),
        "-vf", "ass=" + os.path.join(OUT, "subtitles.ass"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", os.path.join(OUT, "animatic.mp4"),
    ], check=True)

    for tmp in ("_voice.wav", "_mix.wav"):
        os.remove(os.path.join(OUT, tmp))
    print(open(os.path.join(OUT, "timeline.txt"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
