from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent.parent / ".auth" / "vsco_playwright_profile"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"Playwright not available: {exc}")
        return 1

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://vsco.co/", wait_until="domcontentloaded", timeout=60000)
        print("VSCO login browser is open. Sign in, then close the browser window when done.")

        try:
            while True:
                if context.is_closed():
                    break
                if len(context.pages) == 0:
                    break
                context.pages[0].wait_for_timeout(1000)
        except Exception:
            pass

        try:
            context.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())