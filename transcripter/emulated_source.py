import time

def main() -> None: 
    counter = 0
    while True: 
        print(counter)
        counter += 1
        time.sleep(1)

if __name__ == "__main__": 
    main()