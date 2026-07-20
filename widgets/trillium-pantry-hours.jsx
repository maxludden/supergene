//
// Trillium Food Pantry — hours widget (ScriptWidget)
//
// Tap the clock icon to open the weekly-hours view; tap the
// xmark to close it. Interactive buttons need iOS 17+; a tap
// re-runs the whole script, so the open/closed view flag lives
// in $storage rather than an in-memory variable.
//

const now = new Date();

const day = now.toLocaleString('en-US', { weekday: 'long' });
const minutesNow = now.getHours() * 60 + now.getMinutes();

function isBetween(start, end) {
  return minutesNow >= start && minutesNow < end;
}

// Weekly schedule (in minutes since midnight)
const schedule = {
  Monday: [[13 * 60, 16 * 60]],
  Tuesday: [],
  Wednesday: [[9 * 60, 12 * 60], [14 * 60, 16 * 60]],
  Thursday: [[13 * 60, 16 * 60]],
  Friday: [[9 * 60, 13 * 60]],
  Saturday: [],
  Sunday: []
};

// Check if currently open
let open = false;
let closesAt = null;
const todayHours = schedule[day] || [];

for (const [start, end] of todayHours) {
  if (isBetween(start, end)) {
    open = true;
    closesAt = end;
    break;
  }
}

// Helper: format minutes → 12-hour clock ("9:00 AM")
function formatTime(mins) {
  const h24 = Math.floor(mins / 60);
  const m = mins % 60;
  const period = h24 >= 12 ? 'PM' : 'AM';
  const h = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h}:${String(m).padStart(2, '0')} ${period}`;
}

// Helper: format a day's ranges → "9:00 AM – 12:00 PM, 2:00 PM – 4:00 PM"
function formatHours(ranges) {
  if (!ranges || ranges.length === 0) return 'Closed';
  return ranges
    .map(([start, end]) => `${formatTime(start)} – ${formatTime(end)}`)
    .join(', ');
}

// Find next opening time
function getNextOpening() {
  const days = Object.keys(schedule);
  let todayIndex = days.indexOf(day);

  for (let i = 0; i < 7; i++) {
    const checkDay = days[(todayIndex + i) % 7];
    const hours = schedule[checkDay];

    if (hours.length > 0) {
      for (const [start] of hours) {
        if (i > 0 || minutesNow < start) {
          return i === 0
            ? `Opens at ${formatTime(start)}`
            : `Opens ${checkDay} at ${formatTime(start)}`;
        }
      }
    }
  }

  return 'No upcoming hours';
}

const statusText = open ? 'OPEN' : 'CLOSED';
const statusColor = open ? '#2ecc71' : '#e74c3c';

// Current time string (12-hour clock)
const timeString = formatTime(minutesNow);

// Secondary message
const detailText = open
  ? `Open now · closes at ${formatTime(closesAt)}`
  : getNextOpening();

// Simple icon
const icon = open ? '🟢' : '🔴';

// Weekly-hours "modal" state, persisted across the re-render a tap triggers
const showWeekHours = $storage.getString('pantry.showWeekHours') === '1';

const onShowWeekHours = () => {
  $storage.setString('pantry.showWeekHours', '1');
};

const onHideWeekHours = () => {
  $storage.setString('pantry.showWeekHours', '0');
};

// Default view: today's status and hours
const statusView = (
  <vstack padding="12" spacing="4">
    <hstack frame="max">
      <text font="smallTitle">Trillium Food Pantry</text>
      <spacer />
      <button onClick="onShowWeekHours">
        <image systemName="clock" color="gray" />
      </button>
    </hstack>

    <text font="caption" color="gray">
      {day} • {timeString}
    </text>

    <text font="title2" color={statusColor}>
      {icon} {statusText}
    </text>

    <text font="caption" color="gray">
      Today: {formatHours(todayHours)}
    </text>

    <text font="caption" color="gray">
      {detailText}
    </text>
  </vstack>
);

// Weekly view: one row per day, today shown in the default text color
const weekRows = Object.keys(schedule).map((d) =>
  d === day ? (
    <hstack frame="max">
      <text font="caption">{d}</text>
      <spacer />
      <text font="caption">{formatHours(schedule[d])}</text>
    </hstack>
  ) : (
    <hstack frame="max">
      <text font="caption" color="gray">{d}</text>
      <spacer />
      <text font="caption" color="gray">{formatHours(schedule[d])}</text>
    </hstack>
  )
);

const weekView = (
  <vstack padding="12" spacing="4">
    <hstack frame="max">
      <text font="smallTitle">Weekly Hours</text>
      <spacer />
      <button onClick="onHideWeekHours">
        <image systemName="xmark.circle.fill" color="gray" />
      </button>
    </hstack>

    {weekRows}
  </vstack>
);

$render(showWeekHours ? weekView : statusView);
