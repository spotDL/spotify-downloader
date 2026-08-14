CSS = """
.split-pane {
    width: 100%;
    height: 100%;
}

.left-pane {
    width: 42%;
    min-width: 38;
    height: auto;
    max-height: 100%;
    border-right: solid $primary;
    padding: 1;
    overflow-y: auto;
}

.right-pane {
    width: 1fr;
    height: auto;
    max-height: 100%;
    padding: 1;
    overflow-y: auto;
}

.box {
    border: round $primary;
    padding: 1 2;
    width: 100%;
    height: auto;
}

OptionList {
    height: 10;
    border: round $panel;
}

Input:focus,
Select:focus {
    border: round $secondary;
}

#ffmpeg-warn {
    color: $warning;
    margin-top: 1;
}

#menu-box {
    width: 74;
}

.menu-title {
    text-style: bold;
    color: $accent;
    padding: 0 0 1 0;
}

.menu-hint {
    color: $text-muted;
    padding: 1 0 0 0;
}

#query-box {
    width: 100%;
    height: auto;
    overflow-y: auto;
}

.config-row {
    height: auto;
    margin: 0 0 1 0;
}

.half-col {
    width: 1fr;
}

.half-col-left {
    width: 1fr;
    margin-right: 2;
}

#threads-col {
    width: 14;
    margin-right: 2;
}

#dir-col {
    width: 1fr;
}

.dir-browse-row {
    height: auto;
}

.dir-browse-row Input {
    width: 1fr;
}

.dir-browse-row Button {
    width: 7;
    min-width: 7;
    margin-left: 1;
}

#query-box Label {
    text-style: bold;
    color: $accent-lighten-1;
    margin-bottom: 0;
}

#query-box Input,
#query-box Select {
    margin: 0;
}

#query-tabs {
    height: 1fr;
    margin-top: 1;
}

#query-tabs > ContentSwitcher {
    height: 1fr;
}

TabPane {
    height: 100%;
}
.tab-scroll {
    height: 100%;
    overflow-y: auto;
    padding: 0 1;
}

#help-tabs {
    height: 1fr;
}
#help-tabs > ContentSwitcher {
    height: 1fr;
}
#help-tabs TabPane {
    height: 100%;
}
#help-tabs .tab-scroll {
    height: 100%;
    overflow-y: auto;
    padding: 0 1;
}

#query-tabs Label {
    margin: 1 0 0 0;
}
#query-tabs Input,
#query-tabs Select,
#query-tabs Checkbox {
    margin: 0;
}

.section-title {
    text-style: bold;
    color: $accent;
    margin: 1 0 0 0;
    padding: 0;
}

.bottom-buttons {
    height: auto;
    margin-top: 1;
}

.bottom-buttons Button {
    margin-right: 2;
}

.row {
    height: auto;
    align: left middle;
}

.row Button {
    margin-right: 1;
}

#status {
    height: 1;
    color: $warning;
    margin: 1 0 0 0;
}

#track-box {
    width: 100%;
    height: 100%;
}

DataTable {
    height: 1fr;
    border: round $panel;
}

RichLog {
    height: 1fr;
    border: round $panel;
    margin-top: 1;
}

#overall-box {
    height: auto;
    margin-top: 1;
}

#dir-modal {
    width: 90;
    height: 92%;
    border: round $primary;
    padding: 1 2;
}

DirectoryTree {
    height: 1fr;
    border: round $panel;
    margin: 1 0;
}

#simple-box {
    width: 86;
    max-height: 40;
}

.status-bar {
    height: 1;
    background: $surface;
    color: $text;
    text-align: center;
    padding: 0 1;
    border-top: solid $primary;
}

#appbar {
    height: 3;
    dock: top;
    background: $surface;
    border-bottom: solid $primary;
    padding: 0 1;
    align: center middle;
}

#appbar-title {
    width: 1fr;
    color: $accent;
    text-style: bold;
    padding: 0 1;
}

#appbar Button {
    margin-left: 1;
    min-width: 8;
}

#home {
    padding: 1 2;
    height: 1fr;
    overflow-y: auto;
}

#home-welcome {
    text-style: bold;
    color: $accent;
    margin-bottom: 1;
}

.home-cards {
    height: auto;
    margin-bottom: 1;
}

.home-cards Button {
    width: 1fr;
    min-width: 18;
    max-width: 40;
    margin: 0 1 1 0;
    height: 3;
}

.primary-action {
    width: auto;
    margin-top: 1;
}

#home-new-download {
    min-width: 30;
}

#home-recent {
    color: $text-muted;
    margin-top: 1;
}

#add-download {
    height: 1fr;
}

#ad-scroll {
    height: 1fr;
    overflow-y: auto;
    padding: 1 2;
}

#ad-bottom {
    dock: bottom;
    height: auto;
    border-top: solid $primary;
    background: $surface;
    padding: 0 2;
}

#add-download .menu-title {
    margin-bottom: 1;
}

#add-download Collapsible {
    border: round $panel;
    background: $surface;
    padding: 0 1 1 1;
    margin: 1 0;
    width: 100%;
}

#add-download CollapsibleTitle {
    color: $accent;
    text-style: bold;
}

#add-download Switch {
    margin: 0 0 1 0;
}

#add-download SelectionList {
    height: auto;
}

#ad-bottom RichLog {
    height: 3;
    margin: 0;
}

#simple-box {
    width: 86;
    max-height: 90%;
    overflow-y: auto;
}

#simple-box RichLog {
    height: 10;
    margin: 1 0 0 0;
}

#cmd-output {
    height: 12;
}

#lyrics-box {
    width: 80;
    max-width: 90%;
    height: 80%;
    max-height: 90%;
}

#lyrics-body {
    height: 1fr;
    border: round $panel;
    margin: 1 0;
}

Screen.-normal .home-cards,
Screen.-wide .home-cards {
    layout: vertical;
}

Screen.-normal .home-cards Button,
Screen.-wide .home-cards Button {
    width: 100%;
    min-width: 0;
    max-width: 100%;
    margin: 0 0 1 0;
}

Screen.-very-wide #add-download .dir-browse-row {
    width: 1fr;
}
"""
