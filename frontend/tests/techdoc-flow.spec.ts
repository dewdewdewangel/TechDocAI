import { expect, test } from "@playwright/test"

test.skip(
  process.env.RUN_RAG_E2E !== "1",
  "Set RUN_RAG_E2E=1 to run the real BGE and LLM workflow",
)
test.setTimeout(360_000)

const apiUrl = "http://localhost:8000/api/v1"

test("upload, index, ask with citations, and clean up", async ({
  page,
  request,
}) => {
  const suffix = Date.now()
  const title = `E2E deployment guide ${suffix}`
  const question = `Which port does the E2E service use? ${suffix}`
  let documentId: string | undefined
  let sessionId: string | undefined

  await page.goto("/documents")
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  if (!token) throw new Error("Authenticated browser has no access token")
  const apiHeaders = { Authorization: `Bearer ${token}` }

  try {
    await page.getByRole("button", { name: "上传文档" }).click()
    await page.getByLabel("文档标题").fill(title)
    await page.getByLabel("选择文件").setInputFiles({
      name: `e2e-${suffix}.md`,
      mimeType: "text/markdown",
      buffer: Buffer.from(
        "# E2E Service\n\nThe E2E service uses TCP port 43127.\n\nReference: " +
          suffix,
      ),
    })
    const uploadResponsePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/v1/documents/upload" &&
        response.request().method() === "POST",
    )
    await page.getByRole("button", { name: "上传", exact: true }).click()
    const uploadResponse = await uploadResponsePromise
    expect(uploadResponse.ok()).toBeTruthy()
    documentId = ((await uploadResponse.json()) as { id: string }).id

    const documentRow = page.getByRole("row").filter({ hasText: title })
    await expect(documentRow).toBeVisible()
    await expect(documentRow.getByText("已索引")).toBeVisible({
      timeout: 180_000,
    })

    await page.goto("/chat")
    const createResponsePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/v1/chat-sessions/" &&
        response.request().method() === "POST",
    )
    await page.getByTitle("新建会话").click()
    const createResponse = await createResponsePromise
    expect(createResponse.ok()).toBeTruthy()
    sessionId = ((await createResponse.json()) as { id: string }).id

    await page.getByLabel("输入问题").fill(question)
    const askResponsePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname ===
          `/api/v1/chat-sessions/${sessionId}/ask` &&
        response.request().method() === "POST",
    )
    await page.getByTitle("发送问题").click()
    expect((await askResponsePromise).ok()).toBeTruthy()

    await expect(page.getByTestId("chat-message-user").last()).toContainText(
      question,
    )
    const latestAnswer = page.getByTestId("chat-message-assistant").last()
    await expect(latestAnswer).toContainText("43127", { timeout: 120_000 })
    await expect(
      latestAnswer.getByText("参考来源", { exact: true }),
    ).toBeVisible()
    await expect(latestAnswer.getByText(title)).toBeVisible()

    const sessionRow = page
      .getByRole("button", { name: question, exact: true })
      .locator("..")
    await sessionRow.getByTitle("删除会话").click()
    const sessionDeletePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname ===
          `/api/v1/chat-sessions/${sessionId}` &&
        response.request().method() === "DELETE",
    )
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "删除", exact: true })
      .click()
    expect((await sessionDeletePromise).ok()).toBeTruthy()
    sessionId = undefined

    await page.goto("/documents")
    const cleanupRow = page.getByRole("row").filter({ hasText: title })
    await cleanupRow.getByTitle("删除文档").click()
    const documentDeletePromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname ===
          `/api/v1/documents/${documentId}` &&
        response.request().method() === "DELETE",
    )
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "删除", exact: true })
      .click()
    expect((await documentDeletePromise).ok()).toBeTruthy()
    documentId = undefined
    await expect(cleanupRow).toHaveCount(0)
  } finally {
    if (sessionId) {
      await request
        .delete(`${apiUrl}/chat-sessions/${sessionId}`, { headers: apiHeaders })
        .catch(() => undefined)
    }
    if (documentId) {
      await request
        .delete(`${apiUrl}/documents/${documentId}`, { headers: apiHeaders })
        .catch(() => undefined)
    }
  }
})
