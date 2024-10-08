import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { renderWithProviders } from "../../test-utils";
import BrowserPanel from "#/components/Browser";

describe("Browser", () => {
  it("renders a message if no screenshotSrc is provided", () => {
    renderWithProviders(<BrowserPanel />, {
      preloadedState: {
        browser: {
          url: "https://example.com",
          screenshotSrc: "",
        },
      },
    });

    // i18n empty message key
    expect(screen.getByText("BROWSER$EMPTY_MESSAGE")).toBeInTheDocument();
  });

  it("renders the url and a screenshot", () => {
    renderWithProviders(<BrowserPanel />, {
      preloadedState: {
        browser: {
          url: "https://example.com",
          screenshotSrc:
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN0uGvyHwAFCAJS091fQwAAAABJRU5ErkJggg==",
        },
      },
    });

    expect(screen.getByRole("textbox")).toHaveValue("https://example.com");
    expect(screen.getByAltText(/browser screenshot/i)).toBeInTheDocument();
  });
});
