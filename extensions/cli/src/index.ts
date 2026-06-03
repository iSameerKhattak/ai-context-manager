#!/usr/bin/env node

import { Command } from "commander";

const program = new Command();

program
  .name("contextclaw")
  .description("AI-powered Context Management Platform CLI")
  .version("0.1.0");

program
  .command("ask")
  .description("Ask a question about your project")
  .argument("<query>", "the question to ask")
  .option("-p, --project <id>", "project ID")
  .action(async (query: string) => {
    console.log(`ContextClaw: ${query}`);
  });

program
  .command("search")
  .description("Search your project context")
  .argument("<query>", "the search query")
  .option("-p, --project <id>", "project ID")
  .action(async (query: string) => {
    console.log(`Searching: ${query}`);
  });

program
  .command("sync")
  .description("Trigger project re-index")
  .option("-p, --project <id>", "project ID")
  .action(async () => {
    console.log("Syncing project...");
  });

program
  .command("remember")
  .description("Assert a persistent fact")
  .argument("<statement>", "the fact to remember")
  .option("-p, --project <id>", "project ID")
  .action(async (statement: string) => {
    console.log(`Remembered: ${statement}`);
  });

program.parse();
