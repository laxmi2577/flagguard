/**
 * FlagGuard CLI Wrapper
 * 
 * Invokes the FlagGuard Python CLI and parses the JSON output.
 */

import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export interface Conflict {
    id: string;
    flags: string[];
    severity: 'critical' | 'high' | 'medium' | 'low';
    reason: string;
    locations: { file: string; line: number }[];
}

export interface DeadCodeBlock {
    file: string;
    startLine: number;
    endLine: number;
    reason: string;
}

export interface AnalysisResult {
    success: boolean;
    flagsAnalyzed: number;
    conflicts: Conflict[];
    deadCode: DeadCodeBlock[];
    error?: string;
}

export class FlagGuardAnalyzer {
    private outputChannel: vscode.OutputChannel;

    constructor(outputChannel: vscode.OutputChannel) {
        this.outputChannel = outputChannel;
    }

    /**
     * Run FlagGuard analysis on a workspace
     */
    async analyze(workspacePath: string): Promise<AnalysisResult> {
        const config = vscode.workspace.getConfiguration('flagguard');
        const pythonPath = config.get<string>('pythonPath') || 'python';

        // Find config file
        const configFile = await this.findConfigFile(workspacePath);
        if (!configFile) {
            return {
                success: false,
                flagsAnalyzed: 0,
                conflicts: [],
                deadCode: [],
                error: 'No flag configuration file found (flags.json, .flagguard.yaml)',
            };
        }

        // Run FlagGuard CLI
        const command = `${pythonPath} -m flagguard.cli.main analyze --config "${configFile}" --source "${workspacePath}" --format json --no-llm`;

        this.outputChannel.appendLine(`Running: ${command}`);

        return new Promise((resolve) => {
            exec(command, { cwd: workspacePath, timeout: 60000 }, (error, stdout, stderr) => {
                if (error) {
                    this.outputChannel.appendLine(`Error: ${error.message}`);

                    // Try to parse JSON from stderr or stdout even on error
                    try {
                        const result = this.parseOutput(stdout || stderr);
                        resolve(result);
                    } catch {
                        resolve({
                            success: false,
                            flagsAnalyzed: 0,
                            conflicts: [],
                            deadCode: [],
                            error: error.message,
                        });
                    }
                    return;
                }

                try {
                    const result = this.parseOutput(stdout);
                    resolve(result);
                } catch (parseError) {
                    this.outputChannel.appendLine(`Parse error: ${parseError}`);
                    resolve({
                        success: false,
                        flagsAnalyzed: 0,
                        conflicts: [],
                        deadCode: [],
                        error: `Failed to parse output: ${parseError}`,
                    });
                }
            });
        });
    }

    /**
     * Find flag configuration file in workspace
     */
    private async findConfigFile(workspacePath: string): Promise<string | null> {
        const config = vscode.workspace.getConfiguration('flagguard');
        const customPath = config.get<string>('configPath');

        if (customPath && fs.existsSync(customPath)) {
            return customPath;
        }

        const candidates = [
            'flags.json',
            'feature-flags.json',
            '.flagguard.yaml',
            '.flagguard.yml',
            'config/flags.json',
            'src/flags.json',
        ];

        for (const candidate of candidates) {
            const fullPath = path.join(workspacePath, candidate);
            if (fs.existsSync(fullPath)) {
                return fullPath;
            }
        }

        // Try to find any JSON file with "flags" in the name
        const files = await vscode.workspace.findFiles('**/*flag*.json', '**/node_modules/**', 5);
        if (files.length > 0) {
            return files[0].fsPath;
        }

        return null;
    }

    /**
     * Parse FlagGuard JSON output
     */
    private parseOutput(output: string): AnalysisResult {
        // Find JSON in output (may have other text before/after)
        const jsonMatch = output.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            throw new Error('No JSON found in output');
        }

        const data = JSON.parse(jsonMatch[0]);

        const conflicts: Conflict[] = (data.conflicts || []).map((c: any) => ({
            id: c.conflict_id || c.id || 'unknown',
            flags: c.flags_involved || c.flags || [],
            severity: (c.severity || 'medium').toLowerCase(),
            reason: c.reason || 'Unknown conflict',
            locations: (c.affected_locations || []).map((loc: string) => {
                const [file, line] = loc.split(':');
                return { file, line: parseInt(line) || 1 };
            }),
        }));

        const deadCode: DeadCodeBlock[] = (data.dead_code || []).map((d: any) => ({
            file: d.file_path || d.file || '',
            startLine: d.start_line || 1,
            endLine: d.end_line || 1,
            reason: d.reason || 'Unreachable code',
        }));

        return {
            success: true,
            flagsAnalyzed: data.summary?.flags_analyzed || data.flags_analyzed || 0,
            conflicts,
            deadCode,
        };
    }
}
