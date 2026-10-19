import { useMemo, useState } from "react";
import "./App.css";

type Journey = {
    mode: string;
    provider: string;
    price: number;
    duration_minutes: number;
    transfers: number;
    departure_time?: string | null;
    arrival_time?: string | null;
    source_url?: string | null;
};

type Source = { name: string; status: string; url?: string | null };

type SearchResult = {
    origin: string;
    destination: string;
    travel_date: string;
    journeys: Journey[];
    live_results: boolean;
    message: string;
    sources?: Source[];
};

type Category = "all" | "train" | "flight";

const categoryNames: Record<Category, string> = {
    all: "All options",
    train: "Train",
    flight: "Flight",
};

function formatPrice(price: number) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
    }).format(price);
}

function formatDuration(minutes: number) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

function formatTravelDate(value: string) {
    if (!value) return "Choose a date";
    return new Intl.DateTimeFormat("en-IN", {
        weekday: "short",
        day: "numeric",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function localDateOffset(days = 0) {
    const value = new Date();
    value.setDate(value.getDate() + days);
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function parseLocalDate(value: string) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function toLocalDateValue(value: Date) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function categoryFor(journey: Journey): Exclude<Category, "all"> {
    const mode = journey.mode.toLowerCase();
    if (mode.includes("train")) return "train";
    return "flight";
}

function App() {
    const [origin, setOrigin] = useState("");
    const [destination, setDestination] = useState("");
    const [travelDate, setTravelDate] = useState("");
    const [datePickerOpen, setDatePickerOpen] = useState(false);
    const [calendarMonth, setCalendarMonth] = useState(() => {
        const today = new Date();
        return new Date(today.getFullYear(), today.getMonth(), 1);
    });
    const [sortBy, setSortBy] = useState("price");
    const [result, setResult] = useState<SearchResult | null>(null);
    const [category, setCategory] = useState<Category>("all");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const journeys = result?.journeys ?? [];
    const counts = useMemo(() => ({
        all: journeys.length,
        train: journeys.filter((journey) => categoryFor(journey) === "train").length,
        flight: journeys.filter((journey) => categoryFor(journey) === "flight").length,
    }), [journeys]);

    const visibleJourneys = useMemo(() => {
        if (category === "all") return journeys;
        return journeys.filter((journey) => categoryFor(journey) === category);
    }, [category, journeys]);

    const sortedJourneys = useMemo(() => [...visibleJourneys].sort((first, second) => {
        if (sortBy === "duration") {
            return first.duration_minutes - second.duration_minutes || first.price - second.price;
        }
        if (sortBy === "transfers") {
            return first.transfers - second.transfers || first.price - second.price;
        }
        return first.price - second.price || first.duration_minutes - second.duration_minutes;
    }), [sortBy, visibleJourneys]);

    const cheapest = journeys.reduce<Journey | null>(
        (best, journey) => (!best || journey.price < best.price ? journey : best),
        null,
    );
    const fastest = journeys.reduce<Journey | null>(
        (best, journey) => (!best || journey.duration_minutes < best.duration_minutes ? journey : best),
        null,
    );
    const monthTitle = new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric" }).format(calendarMonth);
    const monthStart = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
    const daysInMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0).getDate();
    const leadingDays = (monthStart.getDay() + 6) % 7;
    const calendarDays = [
        ...Array.from({ length: leadingDays }, () => null),
        ...Array.from({ length: daysInMonth }, (_, index) => index + 1),
    ];
    const earliestMonth = parseLocalDate(localDateOffset());
    const previousMonthDisabled = calendarMonth.getFullYear() === earliestMonth.getFullYear()
        && calendarMonth.getMonth() <= earliestMonth.getMonth();

    async function handleSearch(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!travelDate) {
            setError("Choose a travel date before searching.");
            return;
        }
        setLoading(true);
        setError(null);
        setResult(null);
        setCategory("all");

        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 45000);

        try {
            const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
                || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
            const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/search`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                signal: controller.signal,
                body: JSON.stringify({
                    origin,
                    destination,
                    travel_date: travelDate,
                    sort_by: sortBy,
                }),
            });

            if (!response.ok) throw new Error(`Search failed (${response.status})`);
            setResult(await response.json() as SearchResult);
        } catch (cause) {
            setError(
                cause instanceof DOMException && cause.name === "AbortError"
                    ? "This search took too long. Check the backend connection and try again."
                    : cause instanceof Error
                        ? cause.message
                        : "We couldn’t complete that search.",
            );
        } finally {
            window.clearTimeout(timeout);
            setLoading(false);
        }
    }

    return (
        <main className="app-shell">
            <header className="topbar">
                <a className="brand" href="#top" aria-label="Travel Companion home">
                    <span className="brand-mark" aria-hidden="true">↗</span>
                    <span>wayfarer<span className="brand-period">.</span></span>
                </a>
            </header>

            <section className="intro" id="top">
                <p className="eyebrow">TRIP PLANNER</p>
                <h1>Where are you headed?</h1>
                <p className="intro-copy">Compare train and flight options by fare and travel time.</p>
            </section>

            <section className="search-card" aria-label="Journey search">
                <form className="search-form" onSubmit={handleSearch}>
                    <label className="field-group" htmlFor="origin">
                        <span className="field-label">From</span>
                        <span className="field-control">
                            <span className="field-icon origin-icon" aria-hidden="true" />
                            <input id="origin" value={origin} onChange={(event) => setOrigin(event.target.value)} placeholder="City or station" required />
                        </span>
                    </label>

                    <span className="route-connector" aria-hidden="true">→</span>

                    <label className="field-group" htmlFor="destination">
                        <span className="field-label">To</span>
                        <span className="field-control">
                            <span className="field-icon destination-icon" aria-hidden="true" />
                            <input id="destination" value={destination} onChange={(event) => setDestination(event.target.value)} placeholder="Where to?" required />
                        </span>
                    </label>

                    <div className="date-field-group">
                        <div className="field-group">
                            <span className="field-label">Travel date</span>
                            <div className="date-control-wrap">
                                <button
                                    className="field-control date-trigger"
                                    id="travel-date"
                                    type="button"
                                    aria-haspopup="dialog"
                                    aria-expanded={datePickerOpen}
                                    onClick={() => {
                                        if (!datePickerOpen && travelDate) {
                                            const selected = parseLocalDate(travelDate);
                                            setCalendarMonth(new Date(selected.getFullYear(), selected.getMonth(), 1));
                                        }
                                        setDatePickerOpen(!datePickerOpen);
                                    }}
                                >
                                    <span className="calendar-icon" aria-hidden="true">▦</span>
                                    <span className={travelDate ? "date-value" : "date-placeholder"}>
                                        {travelDate ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(parseLocalDate(travelDate)) : "Choose a date"}
                                    </span>
                                    <span className="date-caret" aria-hidden="true">▾</span>
                                </button>
                                {datePickerOpen && (
                                    <div className="calendar-popover" role="dialog" aria-label="Choose travel date">
                                        <div className="calendar-heading">
                                            <strong>{monthTitle}</strong>
                                            <div>
                                                <button type="button" aria-label="Previous month" disabled={previousMonthDisabled} onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1))}>‹</button>
                                                <button type="button" aria-label="Next month" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1))}>›</button>
                                            </div>
                                        </div>
                                        <div className="calendar-grid calendar-weekdays" aria-hidden="true">
                                            {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((day) => <span key={day}>{day}</span>)}
                                        </div>
                                        <div className="calendar-grid" role="grid">
                                            {calendarDays.map((day, index) => {
                                                if (day === null) return <span className="calendar-empty" key={`empty-${index}`} />;
                                                const dateValue = toLocalDateValue(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), day));
                                                const isSelected = dateValue === travelDate;
                                                const isPast = dateValue < localDateOffset();
                                                return (
                                                    <button
                                                        aria-label={new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric" }).format(parseLocalDate(dateValue))}
                                                        aria-selected={isSelected}
                                                        className={`calendar-day ${isSelected ? "selected" : ""}`}
                                                        disabled={isPast}
                                                        key={dateValue}
                                                        onClick={() => { setTravelDate(dateValue); setDatePickerOpen(false); }}
                                                        role="gridcell"
                                                        type="button"
                                                    >{day}</button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="date-shortcuts" aria-label="Quick travel dates">
                            <button type="button" onClick={() => { setTravelDate(localDateOffset()); setDatePickerOpen(false); }}>Today</button>
                            <button type="button" onClick={() => { setTravelDate(localDateOffset(1)); setDatePickerOpen(false); }}>Tomorrow</button>
                        </div>
                    </div>

                    <button className="search-button" type="submit" disabled={loading}>
                        {loading ? <><span className="spinner" /> Searching</> : <>Search journeys <span aria-hidden="true">→</span></>}
                    </button>
                </form>
            </section>

            {error && <div className="error-banner" role="alert">{error}</div>}

            {loading && (
                <section className="loading-panel" aria-live="polite">
                    <span className="spinner spinner-dark" />
                    <div><strong>Finding your options</strong><p>Checking the selected travel sources…</p></div>
                </section>
            )}

            {result && !loading && (
                <section className="results-area" aria-live="polite">
                    <div className="results-heading">
                        <div>
                            <p className="eyebrow">YOUR SEARCH</p>
                            <h2>{result.origin} <span>→</span> {result.destination}</h2>
                            <p className="results-date">{formatTravelDate(result.travel_date)}</p>
                        </div>
                        <div className={`result-count ${journeys.length ? "has-results" : ""}`}>
                            <span className="status-dot" /> {journeys.length} {journeys.length === 1 ? "option" : "options"} found
                        </div>
                    </div>

                    {journeys.length > 0 && (
                        <div className="summary-grid" aria-label="Trip summary">
                            <article className="summary-card summary-featured">
                                <span className="summary-kicker">LOWEST FARE</span>
                                <strong>{formatPrice(cheapest!.price)}</strong>
                                <span>{cheapest!.provider} · {cheapest!.mode}</span>
                            </article>
                            <article className="summary-card">
                                <span className="summary-kicker">QUICKEST TRIP</span>
                                <strong>{formatDuration(fastest!.duration_minutes)}</strong>
                                <span>{fastest!.provider} · {fastest!.mode}</span>
                            </article>
                            <article className="summary-card">
                                <span className="summary-kicker">WAYS TO TRAVEL</span>
                                <strong>{journeys.length}</strong>
                                <span>{["train", "flight"].filter((mode) => counts[mode as Exclude<Category, "all">] > 0).length} categories with options</span>
                            </article>
                        </div>
                    )}

                    <div className="category-toolbar">
                        <div className="category-tabs" role="tablist" aria-label="Filter by travel type">
                            {(Object.keys(categoryNames) as Category[]).map((item) => (
                                <button
                                    className={`category-tab ${category === item ? "active" : ""}`}
                                    key={item}
                                    type="button"
                                    role="tab"
                                    aria-selected={category === item}
                                    onClick={() => setCategory(item)}
                                >
                                    {categoryNames[item]} <span>{counts[item]}</span>
                                </button>
                            ))}
                        </div>
                        <label className="results-sort" htmlFor="sort-results">
                            <span>Sort</span>
                            <select id="sort-results" value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                                <option value="price">Lowest price</option>
                                <option value="duration">Shortest trip</option>
                                <option value="transfers">Fewest transfers</option>
                            </select>
                        </label>
                    </div>

                    {sortedJourneys.length ? (
                        <div className="journey-list">
                            {sortedJourneys.map((journey, index) => (
                                <article className="journey-card" key={`${journey.mode}-${journey.provider}-${journey.departure_time ?? ""}-${journey.arrival_time ?? ""}-${journey.price}-${index}`}>
                                    <div className={`mode-marker mode-${categoryFor(journey)}`} aria-hidden="true">
                                        {categoryFor(journey) === "train" ? "T" : "F"}
                                    </div>
                                    <div className="journey-main">
                                        <div className="journey-title-row">
                                            <h3>{journey.provider}</h3>
                                            <span className={`mode-pill mode-pill-${categoryFor(journey)}`}>{journey.mode}</span>
                                        </div>
                                        <div className="journey-details">
                                            {(journey.departure_time || journey.arrival_time) && (
                                                <span className="journey-times">{journey.departure_time ?? "—"}<span>→</span>{journey.arrival_time ?? "—"}</span>
                                            )}
                                            <span>{formatDuration(journey.duration_minutes)}</span>
                                            <span>{journey.transfers === 0 ? "Direct" : `${journey.transfers} ${journey.transfers === 1 ? "transfer" : "transfers"}`}</span>
                                        </div>
                                    </div>
                                    <div className="journey-price">
                                        <strong>{formatPrice(journey.price)}</strong>
                                        <span>per traveller</span>
                                    </div>
                                    {journey.source_url && (
                                        <a className="journey-source-link" href={journey.source_url} target="_blank" rel="noreferrer">
                                            Check source <span aria-hidden="true">↗</span>
                                        </a>
                                    )}
                                </article>
                            ))}
                        </div>
                    ) : (
                        <div className="empty-state">
                            <span className="empty-icon" aria-hidden="true">⌕</span>
                            <h3>{journeys.length ? `No ${categoryNames[category].toLowerCase()} options` : "No journeys to compare yet"}</h3>
                            <p>{journeys.length ? "Try another category to see more ways to travel." : "We couldn’t find options for this search. Check the source status below or try another route or date."}</p>
                        </div>
                    )}

                    {result.sources?.length ? (
                        <details className="source-details">
                            <summary>Source checks <span>{result.message}</span></summary>
                            <ul>{result.sources.map((source) => <li key={source.name}><span>{source.name}</span><span>{source.status}</span></li>)}</ul>
                        </details>
                    ) : null}
                </section>
            )}

            <footer className="page-footer"><span>wayfarer<span className="brand-period">.</span></span><span>Plan well. Go farther.</span></footer>
        </main>
    );
}

export default App;
