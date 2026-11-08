#!/usr/bin/env python3
# Создаёт озвучку английских фраз для курса.
# Подготовка (один раз):   pip install edge-tts
# Запуск:                  python make_audio.py
# Результат: папка audio/ с файлами .mp3. Положите её рядом с index.html на хостинге.
# Скрипт можно останавливать и запускать снова: готовые файлы он пропускает.
import asyncio, json, os, struct, sys

VOICE = "en-US-AriaNeural"   # другие: en-US-JennyNeural (женский), en-US-GuyNeural (мужской)
RATE = "-10%"                # чуть медленнее обычного, для учёбы
PARALLEL = 3                 # сколько файлов создавать одновременно
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "audio")

def ak(s):
    """Ключ фразы. Должен совпадать с функцией ak() в index.html."""
    s = " ".join(str(s).split())
    b = s.encode("utf-16-le")
    units = struct.unpack("<%dH" % (len(b) // 2), b)
    M = 0xFFFFFFFF
    h1, h2 = 0xDEADBEEF, 0x41C6CE57
    for c in units:
        h1 = ((h1 ^ c) * 2654435761) & M
        h2 = ((h2 ^ c) * 1597334677) & M
    h1 = ((((h1 ^ (h1 >> 16)) * 2246822507) & M) ^ (((h2 ^ (h2 >> 13)) * 3266489909) & M))
    h2 = ((((h2 ^ (h2 >> 16)) * 2246822507) & M) ^ (((h1 ^ (h1 >> 13)) * 3266489909) & M))
    n = 4294967296 * (h2 & 2097151) + (h1 & M)
    d = "0123456789abcdefghijklmnopqrstuvwxyz"
    r = ""
    while n:
        n, m = divmod(n, 36)
        r = d[m] + r
    return r or "0"

async def main():
    try:
        import edge_tts
    except ImportError:
        print("Сначала установите библиотеку:  pip install edge-tts")
        return
    phrases = json.load(open(os.path.join(HERE, "phrases.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    todo = [p for p in phrases if not os.path.exists(os.path.join(OUT, ak(p) + ".mp3"))]
    print(f"Всего фраз: {len(phrases)}, осталось создать: {len(todo)}")
    sem = asyncio.Semaphore(PARALLEL)
    done = [0]
    failed = []

    async def one(p):
        final = os.path.join(OUT, ak(p) + ".mp3")
        tmp = final + ".part"
        async with sem:
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(p, VOICE, rate=RATE).save(tmp)
                    if os.path.getsize(tmp) > 500:
                        os.replace(tmp, final)
                        break
                except Exception:
                    pass
                await asyncio.sleep(2 + attempt * 3)
            else:
                failed.append(p)
        done[0] += 1
        if done[0] % 50 == 0 or done[0] == len(todo):
            print(f"  готово {done[0]} из {len(todo)}")

    await asyncio.gather(*(one(p) for p in todo))
    size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".mp3"))
    print(f"Файлов в audio/: {len([f for f in os.listdir(OUT) if f.endswith('.mp3')])}, размер: {size // 1024 // 1024} МБ")
    if failed:
        print(f"Не удалось создать {len(failed)} фраз. Запустите скрипт ещё раз: он доделает только их.")

if __name__ == "__main__":
    asyncio.run(main())
