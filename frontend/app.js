document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("review-form");
  const outputCard = document.getElementById("output-card");
  const cliCommand = document.getElementById("cli-command");

  if (!form) return;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.getElementById("business-name").value.trim();
    const website = document.getElementById("website-url").value.trim();
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "client";

    cliCommand.textContent = [
      `# Run FounderReach read-only client review for ${name} (${website})`,
      `python -m founderreach.cli client-review \\`,
      `  --profile profiles/${slug}.json \\`,
      `  --permission live_permission.json \\`,
      `  --live-site \\`,
      `  --output reports/${slug}_client_review.md`
    ].join("\n");
    outputCard.hidden = false;
  });
});
