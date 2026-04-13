const APP_URL = "http://localhost:8501/";
const MENU_ID = "send-to-resume-tailor";

function buildAppUrl(jdText = "") {
  const url = new URL(APP_URL);
  const trimmed = jdText.trim();
  if (trimmed) {
    url.searchParams.set("jd", trimmed);
  }
  return url.toString();
}

function openResumeTailor(jdText = "") {
  chrome.tabs.create({ url: buildAppUrl(jdText) });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Send selected JD to Resume Tailor",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId === MENU_ID) {
    openResumeTailor(info.selectionText || "");
  }
});

chrome.action.onClicked.addListener(() => {
  openResumeTailor();
});
