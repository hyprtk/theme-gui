"""Entry point for theme-gui."""
import sys

from .app import ThemeGuiApp


def main():
    app = ThemeGuiApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
