/**
 * Status Bar Manager
 * 
 * Manages the FlagGuard status bar item showing analysis status.
 */

import * as vscode from 'vscode';

export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        this.statusBarItem.command = 'flagguard.analyze';
        this.setIdle();
        this.statusBarItem.show();
    }

    /**
     * Set idle state (no analysis running)
     */
    setIdle(): void {
        this.statusBarItem.text = '$(shield) FlagGuard';
        this.statusBarItem.tooltip = 'Click to analyze feature flags';
        this.statusBarItem.backgroundColor = undefined;
    }

    /**
     * Set analyzing state
     */
    setAnalyzing(): void {
        this.statusBarItem.text = '$(sync~spin) FlagGuard: Analyzing...';
        this.statusBarItem.tooltip = 'Analysis in progress';
        this.statusBarItem.backgroundColor = undefined;
    }

    /**
     * Set success state (no conflicts)
     */
    setSuccess(flagCount: number): void {
        this.statusBarItem.text = `$(check) FlagGuard: ${flagCount} flags OK`;
        this.statusBarItem.tooltip = 'No conflicts detected';
        this.statusBarItem.backgroundColor = undefined;
    }

    /**
     * Set conflicts found state
     */
    setConflicts(conflictCount: number): void {
        this.statusBarItem.text = `$(warning) FlagGuard: ${conflictCount} conflicts`;
        this.statusBarItem.tooltip = 'Click to view conflicts';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }

    /**
     * Set error state
     */
    setError(message: string): void {
        this.statusBarItem.text = '$(error) FlagGuard: Error';
        this.statusBarItem.tooltip = message;
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }

    /**
     * Dispose of resources
     */
    dispose(): void {
        this.statusBarItem.dispose();
    }
}
