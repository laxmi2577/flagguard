/**
 * Hover Provider
 * 
 * Shows flag information when hovering over flag names in code.
 */

import * as vscode from 'vscode';

// Common feature flag patterns
const FLAG_PATTERNS = [
    // Python patterns
    /is_enabled\(['"]([^'"]+)['"]\)/g,
    /get_flag\(['"]([^'"]+)['"]\)/g,
    /feature_enabled\(['"]([^'"]+)['"]\)/g,
    /flag\(['"]([^'"]+)['"]\)/g,
    // JavaScript patterns
    /isEnabled\(['"]([^'"]+)['"]\)/g,
    /getFlag\(['"]([^'"]+)['"]\)/g,
    /featureEnabled\(['"]([^'"]+)['"]\)/g,
    /showFeature\(['"]([^'"]+)['"]\)/g,
    // LaunchDarkly
    /variation\(['"]([^'"]+)['"]/g,
    /ldclient\.variation\(['"]([^'"]+)['"]/g,
];

export class HoverProvider implements vscode.HoverProvider {
    /**
     * Provide hover information
     */
    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Hover> {
        const range = document.getWordRangeAtPosition(position);
        if (!range) {
            return null;
        }

        const lineText = document.lineAt(position.line).text;
        const word = document.getText(range);

        // Check if this word is within a flag pattern
        for (const pattern of FLAG_PATTERNS) {
            pattern.lastIndex = 0;
            let match;
            while ((match = pattern.exec(lineText)) !== null) {
                const flagName = match[1];
                const startIndex = match.index + match[0].indexOf(flagName);
                const endIndex = startIndex + flagName.length;

                if (position.character >= startIndex && position.character <= endIndex) {
                    return this.createFlagHover(flagName);
                }
            }
        }

        // Check if word looks like a flag name
        if (this.looksLikeFlagName(word)) {
            return this.createFlagHover(word);
        }

        return null;
    }

    /**
     * Check if a word looks like a feature flag name
     */
    private looksLikeFlagName(word: string): boolean {
        // Feature flag naming conventions
        const patterns = [
            /^feature[_-]/i,
            /^flag[_-]/i,
            /^enable[_-]/i,
            /^show[_-]/i,
            /^use[_-]/i,
            /[_-]feature$/i,
            /[_-]flag$/i,
            /[_-]enabled$/i,
        ];

        return patterns.some(p => p.test(word));
    }

    /**
     * Create hover content for a flag
     */
    private createFlagHover(flagName: string): vscode.Hover {
        const markdown = new vscode.MarkdownString();
        markdown.isTrusted = true;

        markdown.appendMarkdown(`### 🚩 Feature Flag: \`${flagName}\`\n\n`);
        markdown.appendMarkdown('---\n\n');
        markdown.appendMarkdown('**FlagGuard Analysis**\n\n');
        markdown.appendMarkdown('Run analysis to check for conflicts:\n\n');
        markdown.appendMarkdown('[Analyze Workspace](command:flagguard.analyze)\n\n');
        markdown.appendMarkdown('---\n');
        markdown.appendMarkdown('*Powered by FlagGuard*');

        return new vscode.Hover(markdown);
    }
}
