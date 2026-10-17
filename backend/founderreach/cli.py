import argparse
import sys
import json
from pathlib import Path
from typing import Optional

# Ensure UTF-8 stdout on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from founderreach.models import ProductProfile

console = Console(force_terminal=True, legacy_windows=False)

def cmd_find(args):
    """Find verified customer opportunities."""
    from founderreach.engine import engine
    from founderreach.profiles import load_profile
    profile = load_profile(args.profile)
    console.print(f"\n[bold cyan]🔍 FounderReach AI Discovery Engine[/bold cyan]")
    console.print(f"Product: [green]{profile.name}[/green] ({profile.website})")
    console.print(f"Minimum Score Threshold: [yellow]{args.threshold if args.threshold is not None else profile.minimum_score}[/yellow] | Limit: [yellow]{args.limit}[/yellow]")
    console.print(f"Active Connectors: Hacker News (Public API) | Reddit (Disabled by policy)\n")

    with console.status("[bold green]Discovering, deduplicating, scoring and verifying opportunities...[/bold green]"):
        opps = engine.find_opportunities(
            product=profile,
            min_score=args.threshold,
            limit=args.limit,
            verify_live=not args.no_verify,
            actionable_only=not args.research,
            persist=False
        )

    if not opps:
        if not args.research:
            console.print("[yellow]Honest Result: 0 verified, timely demand signals met the profile threshold.[/yellow]")
            console.print("[dim]Tip: Run with `--research` to inspect historical and observational research insights.[/dim]")
        else:
            console.print("[yellow]Honest Result: No opportunities or research insights met the criteria.[/yellow]")
        return

    if args.format == "json":
        data = [o.model_dump(mode="json") for o in opps]
        print(json.dumps(data, indent=2))
        return

    table = Table(title=f"Verified Discussions for {profile.name}", box=box.ROUNDED)
    table.add_column("Type", style="bold", width=12)
    table.add_column("Score", style="bold green", width=7)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Author", style="magenta", width=14)
    table.add_column("Customer Problem / Evidence Excerpt", style="white", width=42)
    table.add_column("Original URL", style="blue underline", width=36)

    for o in opps:
        type_badge = "[bold green]TIMELY DEMAND[/bold green]" if o.classification == "ACTIONABLE_OPPORTUNITY" else "[yellow]RESEARCH[/yellow]"
        summary_text = f"[bold]{o.customer_problem}[/bold]\n\n[italic dim]\"{o.evidence_excerpt[:130]}...\"[/italic dim]"
        table.add_row(
            type_badge,
            f"{o.score.total_score:.1f}",
            o.discussion_date or "N/A",
            o.author or "Anonymous",
            summary_text,
            o.original_url
        )

    console.print(table)
    console.print(f"\n[bold green]Found {len(opps)} items.[/bold green] Run [dim]`python -m founderreach.cli detail <id>`[/dim] to inspect full verification audit.")

def cmd_detail(args):
    """Display full details and suggested response for an opportunity."""
    from founderreach.db import db
    opps = db.get_opportunities(min_score=0)
    match = None
    for o in opps:
        if o.id.startswith(args.id) or args.id in o.original_url:
            match = o
            break

    if not match:
        console.print(f"[red]Error: Opportunity matching '{args.id}' not found in database.[/red]")
        return

    type_color = "green" if match.classification == "ACTIONABLE_OPPORTUNITY" else "yellow"
    rejection_str = "\n".join([f"  • {r}" for r in match.rejection_reasons]) if match.rejection_reasons else "  • None (Meets all actionable criteria)"

    console.print(Panel(
        f"[bold]Platform:[/bold] {match.platform}\n"
        f"[bold]URL:[/bold] {match.original_url}\n"
        f"[bold]Date:[/bold] {match.discussion_date or 'Unknown'} | [bold]Author:[/bold] {match.author or 'Anonymous'}\n"
        f"[bold]Classification:[/bold] [{type_color}]{match.classification}[/{type_color}]\n"
        f"[bold]Source Status:[/bold] {'[green]SOURCE_VERIFIED (HTTP 200)[/green]' if match.source_status == 'SOURCE_VERIFIED' else '[red]SOURCE_UNVERIFIED[/red]'}\n"
        f"[bold]Customer Intent:[/bold] {'[green]CUSTOMER_INTENT_VERIFIED[/green]' if match.intent_status == 'CUSTOMER_INTENT_VERIFIED' else '[yellow]CUSTOMER_INTENT_UNVERIFIED[/yellow]'}\n"
        f"[bold]Direct Evidence Sentence:[/bold] {f'[italic]{match.direct_problem_evidence}[/italic]' if match.direct_problem_evidence else '[dim]None (Unverified or inferred)[/dim]'}\n"
        f"[bold]Actionability Notes / Rejections:[/bold]\n{rejection_str}\n\n"
        f"[bold]Total Score:[/bold] [green]{match.score.total_score}/100[/green]\n"
        f"  - Problem Fit: {match.score.problem_fit}/30\n"
        f"  - Customer Fit: {match.score.customer_fit}/20\n"
        f"  - Intent: {match.score.expressed_intent}/20\n"
        f"  - Recency: {match.score.recency}/15\n"
        f"  - Evidence Quality: {match.score.evidence_quality}/15\n\n"
        f"[bold cyan]Customer Problem:[/bold cyan]\n{match.customer_problem}\n\n"
        f"[bold cyan]Why Relevant:[/bold cyan]\n{match.why_relevant}\n\n"
        f"[bold cyan]Verified Evidence Excerpt:[/bold cyan]\n[italic]\"{match.evidence_excerpt}\"[/italic]\n\n"
        f"[bold yellow]Suggested Grounded Response (No fabricated claims):[/bold yellow]\n\n"
        f"{match.suggested_response}",
        title=f"Opportunity {match.id[:8]}",
        border_style="cyan"
    ))

def cmd_verify(args):
    """Perform live HTTP verification of an URL and excerpt."""
    from founderreach.validation.verifier import source_verifier
    console.print(f"Verifying live source: [blue]{args.url}[/blue]")
    verif = source_verifier.verify_source(args.url, args.excerpt or "")
    if verif.verified:
        console.print(f"[bold green]✔ VERIFIED[/bold green] (HTTP {verif.http_status}): {verif.verification_notes}")
    else:
        console.print(f"[bold red]✖ REJECTED[/bold red]: {verif.verification_notes}")

def cmd_budget(args):
    """Audit financial spending ledger."""
    from founderreach.ai.cost_tracker import cost_tracker
    summary = cost_tracker.get_spending_summary()
    table = Table(title="FounderReach AI Budget & Financial Audit", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Actual External Spend (INR)", f"INR {summary['spent_inr']:.2f}")
    table.add_row("Actual External Spend (USD)", f"${summary['spent_usd']:.4f}")
    table.add_row("Target Budget Ceiling (INR)", f"INR {summary['target_budget_inr']:.2f}")
    table.add_row("Absolute Spending Ceiling (INR)", f"INR {summary['ceiling_budget_inr']:.2f}")
    table.add_row("Authorized New Spend (INR)", f"INR {summary['authorized_new_spend_inr']:.2f}")
    table.add_row("Remaining to Target (INR)", f"INR {summary['remaining_target_inr']:.2f}")
    table.add_row("Requires CEO Approval", "YES" if summary['requires_ceo_approval'] else "NO")
    table.add_row("Ceiling Status", "[green]HEALTHY / ZERO SPEND[/green]" if summary['is_within_ceiling'] else "[red]EXCEEDED[/red]")

    console.print(table)

def cmd_feedback(args):
    """Legacy feedback writes remain disabled until tenant authorization."""
    console.print("[red]Feedback writes are disabled until tenant authorization is integrated.[/red]")

def cmd_serve(args):
    """Launch lightweight FastAPI server."""
    import uvicorn
    console.print(f"[bold green]Starting FounderReach AI UI on http://localhost:{args.port}[/bold green]")
    uvicorn.run("founderreach.web.app:app", host="127.0.0.1", port=args.port, reload=False)


def cmd_client_review(args):
    """Run a founder-confirmed, permission-scoped M1–M4 client review."""
    from founderreach.client_review import run_client_review

    identifier = args.business_id or input("Business ID (lowercase slug): ").strip()
    name = args.name or input("Business name: ").strip()
    description = args.description or input("Business description: ").strip()
    draft = ProductProfile(identifier=identifier, name=name, description=description,
                           website=args.url, confirmed=False,
                           target_audiences=args.audience or [], pain_points=args.pain_point or [])
    print("Review this business profile:\n" + json.dumps({
        "business_id": draft.identifier, "name": draft.name,
        "website": str(draft.website) if draft.website else None,
        "description": draft.description, "audiences": draft.target_audiences,
        "pain_points": draft.pain_points,
    }, ensure_ascii=True, indent=2))
    if input("Type CONFIRM to self-declare this profile is correct (identity is not verified; authorization is self-declared and does not prove site ownership): ").strip() != "CONFIRM":
        raise PermissionError("Founder confirmation was not given")
    profile = ProductProfile.model_validate({**draft.model_dump(mode="json"), "confirmed": True})
    result = run_client_review(profile,
        permission_path=Path(args.permission) if args.permission else None,
        fixture_path=Path(args.fixtures) if args.fixtures else None,
        attestations_path=Path(args.attestations) if args.attestations else None,
        live_site=bool(args.live_site))
    if args.report:
        with Path(args.report).open("x", encoding="utf-8") as output:
            output.write(result.report)
        print(f"Local report: {args.report}")
    else:
        print(result.report)

def main(argv=None):
    parser = argparse.ArgumentParser(description="FounderReach AI: Verified Customer Opportunity Finder")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # find
    p_find = subparsers.add_parser("find", help="Find customer opportunities")
    p_find.add_argument("--profile", default="careflow", help="Founder-confirmed profile identifier")
    p_find.add_argument("--threshold", type=int, default=None, help="Minimum 100-pt score threshold (default: profile setting)")
    p_find.add_argument("--limit", type=int, default=10, help="Maximum opportunities to return (default: 10)")
    p_find.add_argument("--format", choices=["table", "json", "markdown"], default="table", help="Output format")
    p_find.add_argument("--no-verify", action="store_true", help="Bypass live HTTP verification (not recommended)")
    p_find.add_argument("--research", action="store_true", help="Include historical/observational research insights (default: actionable opportunities only)")
    p_find.set_defaults(func=cmd_find)

    # detail
    p_detail = subparsers.add_parser("detail", help="View full details and suggested response for an opportunity")
    p_detail.add_argument("id", help="Opportunity ID or URL substring")
    p_detail.set_defaults(func=cmd_detail)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify live URL and excerpt")
    p_verify.add_argument("--url", required=True, help="URL to verify")
    p_verify.add_argument("--excerpt", default="", help="Excerpt to check in page content")
    p_verify.set_defaults(func=cmd_verify)

    # budget
    p_budget = subparsers.add_parser("budget", help="Show spending ledger and cost tracking")
    p_budget.set_defaults(func=cmd_budget)

    # feedback
    p_feedback = subparsers.add_parser("feedback", help="Record feedback on opportunity quality")
    p_feedback.add_argument("--id", required=True, help="Opportunity ID")
    p_feedback.add_argument("--status", choices=["relevant", "irrelevant"], required=True)
    p_feedback.add_argument("--notes", default=None, help="Founder review notes")
    p_feedback.set_defaults(func=cmd_feedback)

    # serve
    p_serve = subparsers.add_parser("serve", help="Launch lightweight web dashboard")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to run web app (default: 8000)")
    p_serve.set_defaults(func=cmd_serve)

    # Founder-confirmed client review (offline fixture default or bounded live HTTPS audit).
    p_review = subparsers.add_parser(
        "client-review",
        help="Evidence-linked client review (authorization is self-declared and does not prove site ownership)",
        description="Run a permission-scoped client review. Authorization is self-declared and does not prove site ownership.",
    )
    p_review.add_argument("--url", help="Exact HTTPS page URL to review (from local fixtures by default, or live with --live-site)")
    p_review.add_argument("--business-id", help="Stable lowercase business slug")
    p_review.add_argument("--name", help="Business name")
    p_review.add_argument("--description", help="Business description")
    p_review.add_argument("--audience", action="append", help="Target audience; repeat if needed")
    p_review.add_argument("--pain-point", action="append", help="Problem solved; repeat if needed")
    p_review.add_argument("--permission", help="Local exact-origin permission JSON (authorization is self-declared and does not prove site ownership)")
    p_review.add_argument("--fixtures", help="Local bounded HTML fixture JSON (offline mode only)")
    p_review.add_argument("--live-site", action="store_true", help="Fetch only approved HTTPS URLs live (authorization is self-declared and does not prove site ownership)")
    p_review.add_argument("--attestations", help="Optional minimized founder attestation JSON")
    p_review.add_argument("--report", help="New local Markdown report path; never overwrites")
    p_review.set_defaults(func=cmd_client_review)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)

if __name__ == "__main__":
    main()
