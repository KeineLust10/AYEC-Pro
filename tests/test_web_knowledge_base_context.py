from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_knowledge_base_context_menu_matches_desktop_delete_and_copy_actions():
    desktop = (ROOT / "src" / "ui" / "pages" / "knowledge_base_page.py").read_text(encoding="utf-8")
    web = (WEB / "knowledge-base-reference.js").read_text(encoding="utf-8")
    desktop_menu = desktop[desktop.index("def show_context_menu(self, position):"):desktop.index("def delete_article", desktop.index("def show_context_menu(self, position):"))]
    web_menu = web[web.index('menu.innerHTML ='):web.index('document.body.append(menu)', web.index('menu.innerHTML ='))]

    assert "action_delete.triggered.connect(self.delete_article)" in desktop_menu
    assert "QApplication.clipboard().setText(item.data(Qt.ItemDataRole.UserRole))" in desktop_menu
    assert web_menu.index("data-kb-menu-delete") < web_menu.index("data-kb-menu-copy")
    assert 'if (!ayecContextMenuEnabled("knowledge-base")) { event.preventDefault(); return; }' in web
    assert 'deleteArticle(meta, targetArticle)' in web
    assert 'copyArticle(targetArticle)' in web
    assert "navigator.clipboard.writeText" in web
    assert 'document.execCommand("copy")' in web
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "manualUsedPartManifestWorkflow, knowledgeBaseWorkflow: knowledgeBaseWorkflowAudit, modernInputDialogWorkflow" in route_smoke
    assert 'knowledge.deleteCall?.body?._action !== "delete"' in route_smoke
    assert "!knowledge.deleteCancelPreserved" in route_smoke
    assert "!knowledge.contextMenuSuppressedBySetting" in route_smoke
    assert "!knowledge.contextMenuSuppressedGlobally" in route_smoke


def test_knowledge_base_delete_offscreen_audit_covers_failure_and_retry():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "QA knowledge article delete unavailable" in route_smoke
    assert "!knowledge.deleteFailureRetained" in route_smoke
    assert "knowledge.deleteAttempts !== 2" in route_smoke
