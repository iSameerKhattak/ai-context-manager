import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  const disposables: vscode.Disposable[] = [];

  disposables.push(
    vscode.commands.registerCommand("contextclaw.chat.open", () => {
      vscode.window.showInformationMessage("ContextClaw Chat opened");
    }),
  );

  disposables.push(
    vscode.commands.registerCommand("contextclaw.explain", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.document.getText(editor.selection);
      if (!selection) {
        vscode.window.showInformationMessage(
          "Select code to explain",
        );
        return;
      }
      vscode.window.showInformationMessage(
        `Explaining: ${selection.slice(0, 50)}...`,
      );
    }),
  );

  disposables.push(
    vscode.commands.registerCommand("contextclaw.memory.assert", async () => {
      const fact = await vscode.window.showInputBox({
        prompt: "Enter a fact to remember",
        placeHolder: "We use TanStack Query, never SWR",
      });
      if (fact) {
        vscode.window.showInformationMessage(`Remembered: ${fact}`);
      }
    }),
  );

  disposables.push(
    vscode.commands.registerCommand("contextclaw.repo.resync", () => {
      vscode.window.showInformationMessage("Resyncing repository...");
    }),
  );

  disposables.push(
    vscode.commands.registerCommand("contextclaw.arch.open", () => {
      vscode.window.showInformationMessage("Opening architecture view...");
    }),
  );

  disposables.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("contextclaw")) {
        // Re-read config
      }
    }),
  );

  context.subscriptions.push(...disposables);
}

export function deactivate() {
  // Cleanup
}
