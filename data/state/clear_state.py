# ./ 하위 모든 json을 날리는 기능
import os
def clear_state_data():
    state_dir = "./"
    # state_dir 하위의 모든 json 파일을 삭제합니다.
    for root, dirs, files in os.walk(state_dir):
        for filename in files:
            if filename.endswith(".json"):
                os.remove(os.path.join(root, filename))
                print(f"Deleted {filename} from {root}")

    print("All state data cleared.")

if __name__ == "__main__":
    clear_state_data()