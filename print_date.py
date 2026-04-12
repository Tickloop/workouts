from datetime import date


def get_today():
    return date.today()


def main():
    print(get_today())


if __name__ == "__main__":
    main()
