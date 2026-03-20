from app.assistant import JarvisAssistant


def main() -> None:
    assistant = JarvisAssistant.from_env()
    assistant.run()


if __name__ == "__main__":
    main()

