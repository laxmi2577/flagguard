/**
 * Code Lens Provider
 * 
 * Shows inline annotations above flag usages.
 */

import * as vscode from 'vscode';

// Flag patterns to detect
const FLAG_PATTERNS = [
    /is_enabled\(['"]([^'"]+)['"]\)/g,
    /isEnabled\(['"]([^'"]+)['"]\)/g,
    /get_flag\(['"]([^'"]+)['"]\)/g,
    /getFlag\(['"]([^'"]+)['"]\)/g,
    /variation\(['"]([^'"]+)['"]/g,
];

export class CodeLensProvider implements vscode.CodeLensProvider {
    private _onDidChangeCodeLenses: vscode.EventEmitter<void> = new vscode.EventEmitter<void>();
    public onDidChangeCodeLenses: vscode.Event<void> = this._onDidChangeCodeLenses.event;

    /**
     * Provide code lenses for flag usages
     */
    provideCodeLenses(
        document: vscode.TextDocument,
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.CodeLens[]> {
        const config = vscode.workspace.getConfiguration('flagguard');
        if (!config.get('enabled')) {
            return [];
        }

        const codeLenses: vscode.CodeLens[] = [];
        const text = document.getText();
        const lines = text.split('\n');
        const foundFlags = new Set<string>();

        for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
            const line = lines[lineIndex];

            for (const pattern of FLAG_PATTERNS) {
                pattern.lastIndex = 0;
                let match;

                while ((match = pattern.exec(line)) !== null) {
                    const flagName = match[1];

                    // Only add one code lens per flag per file
                    if (!foundFlags.has(flagName)) {
                        foundFlags.add(flagName);

                        const range = new vscode.Range(
                            new vscode.Position(lineIndex, 0),
                            new vscode.Position(lineIndex, line.length)
                        );

                        const codeLens = new vscode.CodeLens(range, {
                            title: `🚩 Flag: ${flagName}`,
                            command: 'flagguard.analyze',
                            tooltip: 'Click to analyze this flag for conflicts',
                        });

                        codeLenses.push(codeLens);
                    }
                }
            }
        }

        return codeLenses;
    }

    /**
     * Refresh code lenses
     */
    refresh(): void {
        this._onDidChangeCodeLenses.fire();
    }
}
