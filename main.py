import eel
import module.token_manager as token_manager

if __name__ == "__main__":
    print(token_manager.get_keys())

    eel.init("web")
    eel.start("web/index.html", size=(800, 600))