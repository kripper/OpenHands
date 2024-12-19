import test, { expect, Page } from "@playwright/test";
import { confirmSettings } from "./helpers/confirm-settings";

const toggleConversationPanel = async (page: Page) => {
  const panel = page.getByTestId("conversation-panel");
  const panelIsVisible = await panel.isVisible();

  if (!panelIsVisible) {
    const conversationPanelButton = page.getByTestId(
      "toggle-conversation-panel",
    );
    await conversationPanelButton.click();
  }

  return page.getByTestId("conversation-panel");
};

const selectConversationCard = async (page: Page, index: number) => {
  const panel = await toggleConversationPanel(page);

  // select a conversation
  const conversationItem = panel.getByTestId("conversation-card").nth(index);
  await conversationItem.click();

  // panel should close
  await expect(panel).not.toBeVisible();

  await page.waitForURL(`/conversation?cid=${index + 1}`);
  expect(page.url()).toBe(
    `http://localhost:3001/conversation?cid=${index + 1}`,
  );
};

test("should only display the create new conversation button in /conversation", async ({
  page,
}) => {
  await page.goto("/");
  await confirmSettings(page);
  const panel = await toggleConversationPanel(page);

  const newProjectButton = panel.getByTestId("new-conversation-button");
  await expect(newProjectButton).not.toBeVisible();

  await page.goto("/conversation");
  await expect(newProjectButton).toBeVisible();
});

test("redirect to /conversation with the session id as a query param", async ({
  page,
}) => {
  await page.goto("/");
  await confirmSettings(page);

  const panel = await toggleConversationPanel(page);

  // select a conversation
  const conversationItem = panel.getByTestId("conversation-card").first();
  await conversationItem.click();

  // panel should close
  expect(panel).not.toBeVisible();

  await page.waitForURL("/conversation?cid=1");
  expect(page.url()).toBe("http://localhost:3001/conversation?cid=1");
});

test("redirect to the home screen if the current session was deleted", async ({
  page,
}) => {
  await page.goto("/");
  await confirmSettings(page);

  await page.goto("/conversation?cid=1");
  await page.waitForURL("/conversation?cid=1");

  const panel = page.getByTestId("conversation-panel");
  const firstCard = panel.getByTestId("conversation-card").first();

  const ellipsisButton = firstCard.getByTestId("ellipsis-button");
  await ellipsisButton.click();

  const deleteButton = firstCard.getByTestId("delete-button");
  await deleteButton.click();

  // confirm modal
  const confirmButton = page.getByText("Confirm");
  await confirmButton.click();

  await page.waitForURL("/");
});

test("load relevant files in the file explorer", async ({ page }) => {
  await page.goto("/");
  await confirmSettings(page);
  await selectConversationCard(page, 0);

  // check if the file explorer has the correct files
  const fileExplorer = page.getByTestId("file-explorer");

  await expect(fileExplorer.getByText("file1.txt")).toBeVisible();
  await expect(fileExplorer.getByText("file2.txt")).toBeVisible();
  await expect(fileExplorer.getByText("file3.txt")).toBeVisible();

  await selectConversationCard(page, 2);

  // check if the file explorer has the correct files
  expect(fileExplorer.getByText("reboot_skynet.exe")).toBeVisible();
  expect(fileExplorer.getByText("target_list.txt")).toBeVisible();
  expect(fileExplorer.getByText("terminator_blueprint.txt")).toBeVisible();
});

test("should create a new conversation", async ({ page }) => {
  await page.goto("/");
  await confirmSettings(page);

  await page.goto("/conversation");
  await page.waitForURL("/conversation");

  const conversationPanel = await toggleConversationPanel(page);
  const cards = conversationPanel.getByTestId("conversation-card");

  expect(page.url()).toMatch(/http:\/\/localhost:3001\/conversation\?cid=\d+/);
  await toggleConversationPanel(page);
  expect(cards).toHaveCount(4);
});

test("should redirect to home screen if conversation deos not exist", async ({
  page,
}) => {
  await page.goto("/");
  await confirmSettings(page);

  await page.goto("/conversation?cid=9999");
  await page.waitForURL("/");
});