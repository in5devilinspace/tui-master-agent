package main

import (
	"fmt"
	"os"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
)

type phase int

const (
	phaseWork phase = iota
	phaseShortBreak
	phaseLongBreak
)

func (p phase) String() string {
	switch p {
	case phaseWork:
		return "FOCUS"
	case phaseShortBreak:
		return "SHORT BREAK"
	case phaseLongBreak:
		return "LONG BREAK"
	}
	return ""
}

func (p phase) duration() time.Duration {
	switch p {
	case phaseWork:
		return 25 * time.Minute
	case phaseShortBreak:
		return 5 * time.Minute
	case phaseLongBreak:
		return 15 * time.Minute
	}
	return 0
}

type tickMsg time.Time

func tick() tea.Cmd {
	return tea.Tick(time.Second, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

type model struct {
	current     phase
	remaining   time.Duration
	running     bool
	completed   int // completed work sessions
	width       int
}

func initialModel() model {
	return model{
		current:   phaseWork,
		remaining: phaseWork.duration(),
		running:   false,
		width:     60,
	}
}

func (m model) Init() tea.Cmd {
	return tick()
}

func (m model) nextPhase() phase {
	if m.current != phaseWork {
		return phaseWork
	}
	// Just finished a work session.
	if (m.completed+1)%4 == 0 {
		return phaseLongBreak
	}
	return phaseShortBreak
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
	case tea.KeyPressMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case " ", "space", "p":
			m.running = !m.running
		case "r":
			m.remaining = m.current.duration()
			m.running = false
		case "s":
			// Skip to next phase.
			if m.current == phaseWork {
				m.completed++
			}
			m.current = m.nextPhase()
			m.remaining = m.current.duration()
			m.running = false
		}
	case tickMsg:
		if m.running && m.remaining > 0 {
			m.remaining -= time.Second
			if m.remaining <= 0 {
				m.remaining = 0
				if m.current == phaseWork {
					m.completed++
				}
				m.current = m.nextPhase()
				m.remaining = m.current.duration()
				m.running = false
			}
		}
		return m, tick()
	}
	return m, nil
}

func renderBar(width int, ratio float64) string {
	if width < 10 {
		width = 10
	}
	if ratio < 0 {
		ratio = 0
	}
	if ratio > 1 {
		ratio = 1
	}
	filled := int(float64(width) * ratio)
	if filled > width {
		filled = width
	}
	return "[" + strings.Repeat("=", filled) + strings.Repeat(" ", width-filled) + "]"
}

func formatTime(d time.Duration) string {
	if d < 0 {
		d = 0
	}
	total := int(d.Seconds())
	mins := total / 60
	secs := total % 60
	return fmt.Sprintf("%02d:%02d", mins, secs)
}

func (m model) View() tea.View {
	total := m.current.duration()
	var ratio float64
	if total > 0 {
		ratio = 1.0 - float64(m.remaining)/float64(total)
	}

	barWidth := m.width - 10
	if barWidth < 20 {
		barWidth = 20
	}
	if barWidth > 50 {
		barWidth = 50
	}

	status := "paused"
	if m.running {
		status = "running"
	}

	var tomatoes strings.Builder
	for i := 0; i < 4; i++ {
		if i < m.completed%4 || (m.completed > 0 && m.completed%4 == 0 && i < 4 && m.current == phaseLongBreak) {
			tomatoes.WriteString("o ")
		} else {
			tomatoes.WriteString(". ")
		}
	}

	var b strings.Builder
	b.WriteString("\n  Pomodoro Focus\n")
	b.WriteString("  --------------\n\n")
	b.WriteString(fmt.Sprintf("  Phase:     %s (%s)\n", m.current.String(), status))
	b.WriteString(fmt.Sprintf("  Time:      %s / %s\n", formatTime(m.remaining), formatTime(total)))
	b.WriteString(fmt.Sprintf("  Cycle:     %s\n", tomatoes.String()))
	b.WriteString(fmt.Sprintf("  Completed: %d session(s)\n\n", m.completed))
	b.WriteString("  " + renderBar(barWidth, ratio) + "\n\n")
	b.WriteString("  [space] start/pause   [s] skip   [r] reset   [q] quit\n")

	return tea.NewView(b.String())
}

func main() {
	p := tea.NewProgram(initialModel())
	if _, err := p.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
