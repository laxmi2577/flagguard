/**
 * Diagnostics Manager
 * 
 * Manages VS Code diagnostics (Problems panel) for FlagGuard issues.
 */

import * as vscode from 'vscode';
import { AnalysisResult, Conflict, DeadCodeBlock } from './flagguard';

export class DiagnosticsManager implements vscode.Disposable {
    private diagnosticCollection: vscode.DiagnosticCollection;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('flagguard');
    }

    /**
     * Update diagnostics from analysis result
     */
    updateFromAnalysis(result: AnalysisResult): void {
        this.clear();

        const diagnosticsMap = new Map<string, vscode.Diagnostic[]>();

        // Add conflict diagnostics
        for (const conflict of result.conflicts) {
            for (const location of conflict.locations) {
                const filePath = this.resolveFilePath(location.file);
                const diagnostic = this.createConflictDiagnostic(conflict, location.line);

                const existing = diagnosticsMap.get(filePath) || [];
                existing.push(diagnostic);
                diagnosticsMap.set(filePath, existing);
            }

            // If no locations, add to workspace root
            if (conflict.locations.length === 0) {
                const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
                if (workspaceFolder) {
                    const flagsFile = `${workspaceFolder}/flags.json`;
                    const diagnostic = this.createConflictDiagnostic(conflict, 1);
                    const existing = diagnosticsMap.get(flagsFile) || [];
                    existing.push(diagnostic);
                    diagnosticsMap.set(flagsFile, existing);
                }
            }
        }

        // Add dead code diagnostics
        for (const deadCode of result.deadCode) {
            const filePath = this.resolveFilePath(deadCode.file);
            const diagnostic = this.createDeadCodeDiagnostic(deadCode);

            const existing = diagnosticsMap.get(filePath) || [];
            existing.push(diagnostic);
            diagnosticsMap.set(filePath, existing);
        }

        // Apply all diagnostics
        for (const [filePath, diagnostics] of diagnosticsMap) {
            const uri = vscode.Uri.file(filePath);
            this.diagnosticCollection.set(uri, diagnostics);
        }
    }

    /**
     * Create diagnostic for a conflict
     */
    private createConflictDiagnostic(conflict: Conflict, line: number): vscode.Diagnostic {
        const range = new vscode.Range(
            new vscode.Position(Math.max(0, line - 1), 0),
            new vscode.Position(Math.max(0, line - 1), 100)
        );

        const severity = this.getSeverity(conflict.severity);
        const flagList = conflict.flags.join(', ');

        const diagnostic = new vscode.Diagnostic(
            range,
            `${conflict.id}: ${conflict.reason}\nFlags: ${flagList}`,
            severity
        );

        diagnostic.source = 'FlagGuard';
        diagnostic.code = conflict.id;

        return diagnostic;
    }

    /**
     * Create diagnostic for dead code
     */
    private createDeadCodeDiagnostic(deadCode: DeadCodeBlock): vscode.Diagnostic {
        const range = new vscode.Range(
            new vscode.Position(deadCode.startLine - 1, 0),
            new vscode.Position(deadCode.endLine - 1, 100)
        );

        const diagnostic = new vscode.Diagnostic(
            range,
            `Dead code: ${deadCode.reason}`,
            vscode.DiagnosticSeverity.Hint
        );

        diagnostic.source = 'FlagGuard';
        diagnostic.code = 'dead-code';
        diagnostic.tags = [vscode.DiagnosticTag.Unnecessary];

        return diagnostic;
    }

    /**
     * Map severity string to VS Code DiagnosticSeverity
     */
    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        const config = vscode.workspace.getConfiguration('flagguard');
        const mapping: Record<string, string> = {
            critical: config.get('severity.critical') || 'error',
            high: config.get('severity.high') || 'error',
            medium: config.get('severity.medium') || 'warning',
            low: config.get('severity.low') || 'information',
        };

        const level = mapping[severity] || 'warning';

        switch (level) {
            case 'error': return vscode.DiagnosticSeverity.Error;
            case 'warning': return vscode.DiagnosticSeverity.Warning;
            case 'information': return vscode.DiagnosticSeverity.Information;
            case 'hint': return vscode.DiagnosticSeverity.Hint;
            default: return vscode.DiagnosticSeverity.Warning;
        }
    }

    /**
     * Resolve relative file path to absolute
     */
    private resolveFilePath(filePath: string): string {
        if (filePath.startsWith('/') || filePath.match(/^[A-Z]:/)) {
            return filePath;
        }

        const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (workspaceFolder) {
            return `${workspaceFolder}/${filePath}`;
        }

        return filePath;
    }

    /**
     * Clear all diagnostics
     */
    clear(): void {
        this.diagnosticCollection.clear();
    }

    /**
     * Dispose of resources
     */
    dispose(): void {
        this.diagnosticCollection.dispose();
    }
}
