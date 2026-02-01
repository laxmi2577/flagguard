/**
 * FlagGuard VS Code Extension
 * 
 * Provides real-time feature flag conflict detection in the editor.
 */

import * as vscode from 'vscode';
import { FlagGuardAnalyzer, AnalysisResult } from './flagguard';
import { DiagnosticsManager } from './diagnostics';
import { StatusBarManager } from './statusbar';
import { HoverProvider } from './hover';
import { CodeLensProvider } from './codelens';

let analyzer: FlagGuardAnalyzer;
let diagnosticsManager: DiagnosticsManager;
let statusBarManager: StatusBarManager;
let outputChannel: vscode.OutputChannel;

/**
 * Extension activation - called when extension is loaded
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('FlagGuard extension is now active!');

    // Create output channel for logs
    outputChannel = vscode.window.createOutputChannel('FlagGuard');
    outputChannel.appendLine('FlagGuard extension activated');

    // Initialize components
    analyzer = new FlagGuardAnalyzer(outputChannel);
    diagnosticsManager = new DiagnosticsManager();
    statusBarManager = new StatusBarManager();

    // Register commands
    const analyzeCommand = vscode.commands.registerCommand('flagguard.analyze', async () => {
        await runAnalysis();
    });

    const viewReportCommand = vscode.commands.registerCommand('flagguard.viewReport', async () => {
        await viewReport();
    });

    const configureCommand = vscode.commands.registerCommand('flagguard.configure', () => {
        vscode.commands.executeCommand('workbench.action.openSettings', 'flagguard');
    });

    const clearDiagnosticsCommand = vscode.commands.registerCommand('flagguard.clearDiagnostics', () => {
        diagnosticsManager.clear();
        statusBarManager.setIdle();
        vscode.window.showInformationMessage('FlagGuard diagnostics cleared');
    });

    // Register hover provider
    const hoverProvider = new HoverProvider();
    const hoverDisposable = vscode.languages.registerHoverProvider(
        [
            { scheme: 'file', language: 'python' },
            { scheme: 'file', language: 'javascript' },
            { scheme: 'file', language: 'typescript' },
        ],
        hoverProvider
    );

    // Register code lens provider
    const codeLensProvider = new CodeLensProvider();
    const codeLensDisposable = vscode.languages.registerCodeLensProvider(
        [
            { scheme: 'file', language: 'python' },
            { scheme: 'file', language: 'javascript' },
            { scheme: 'file', language: 'typescript' },
        ],
        codeLensProvider
    );

    // Listen for file saves
    const saveDisposable = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('flagguard');
        if (config.get('enabled') && config.get('analyzeOnSave')) {
            await runAnalysis();
        }
    });

    // Listen for configuration changes
    const configDisposable = vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('flagguard')) {
            outputChannel.appendLine('Configuration changed');
        }
    });

    // Add to subscriptions
    context.subscriptions.push(
        analyzeCommand,
        viewReportCommand,
        configureCommand,
        clearDiagnosticsCommand,
        hoverDisposable,
        codeLensDisposable,
        saveDisposable,
        configDisposable,
        diagnosticsManager,
        statusBarManager,
        outputChannel
    );

    // Run initial analysis if workspace is open
    if (vscode.workspace.workspaceFolders) {
        setTimeout(() => runAnalysis(), 2000);
    }
}

/**
 * Run FlagGuard analysis on the workspace
 */
async function runAnalysis(): Promise<void> {
    const config = vscode.workspace.getConfiguration('flagguard');
    if (!config.get('enabled')) {
        return;
    }

    statusBarManager.setAnalyzing();
    outputChannel.appendLine('Starting analysis...');

    try {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showWarningMessage('No workspace folder open');
            return;
        }

        const workspacePath = workspaceFolders[0].uri.fsPath;
        const result = await analyzer.analyze(workspacePath);

        if (result.success) {
            // Update diagnostics
            diagnosticsManager.updateFromAnalysis(result);

            // Update status bar
            if (result.conflicts.length === 0) {
                statusBarManager.setSuccess(result.flagsAnalyzed);
            } else {
                statusBarManager.setConflicts(result.conflicts.length);
            }

            outputChannel.appendLine(`Analysis complete: ${result.flagsAnalyzed} flags, ${result.conflicts.length} conflicts`);
        } else {
            statusBarManager.setError(result.error || 'Unknown error');
            outputChannel.appendLine(`Analysis failed: ${result.error}`);
        }
    } catch (error) {
        const msg = error instanceof Error ? error.message : String(error);
        statusBarManager.setError(msg);
        outputChannel.appendLine(`Error: ${msg}`);
    }
}

/**
 * Open analysis report in webview
 */
async function viewReport(): Promise<void> {
    const panel = vscode.window.createWebviewPanel(
        'flagguardReport',
        'FlagGuard Report',
        vscode.ViewColumn.One,
        { enableScripts: true }
    );

    panel.webview.html = getReportHtml();
}

/**
 * Generate report HTML
 */
function getReportHtml(): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: var(--vscode-font-family); padding: 20px; }
        h1 { color: var(--vscode-foreground); }
        .card { background: var(--vscode-editor-background); padding: 16px; border-radius: 8px; margin: 8px 0; }
    </style>
</head>
<body>
    <h1>🚩 FlagGuard Analysis Report</h1>
    <div class="card">
        <p>Run analysis using <strong>Ctrl+Shift+P → FlagGuard: Analyze Workspace</strong></p>
        <p>Results will appear in the Problems panel.</p>
    </div>
</body>
</html>`;
}

/**
 * Extension deactivation
 */
export function deactivate() {
    console.log('FlagGuard extension deactivated');
}
