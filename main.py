from __future__ import annotations

import argparse

from app.assistant import JarvisAssistant


def main() -> None:
    parser = argparse.ArgumentParser(description='JarvisAI assistant')
    parser.add_argument('--voice', action='store_true', help='Start the assistant in voice mode')
    args = parser.parse_args()

    assistant = JarvisAssistant.from_env()
    mode = 'voice' if args.voice else None
    assistant.run(mode=mode)


if __name__ == "__main__":
    main()
