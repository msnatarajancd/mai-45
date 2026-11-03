# Compact application shell and chat dock

User-requested refinement: bottom-right assistant bubble, expandable full-screen assistant, menu search at the top, reduced unused spacing, and Bright/Dark modes.

Use one shared chat renderer/state for dock and full screen. Dock is a fixed, responsive native Streamlit container, with close and expand controls; full screen offers a return-to-page/minimize control. No iframe, duplicated conversation, or custom model integration. Render dock before page widgets so confirmed operations can safely update their state before rerender. Emergency interruption suppresses the dock.

Move search to a main top toolbar next to appearance selection, retain matching menu entries in the sidebar, and show direct search result navigation above content. Remove the content max-width that causes large side gutters. Compact sidebar branding and dividers; reduce top/header gaps while keeping mobile sidebar control accessible. Theme uses shared semantic CSS variables for app, panels, text, inputs and chat; appearance stays in session.

Verify dock open/close/expand/minimize preserves transcript and pending proposal; theme and navigation retain application state; all prior tests; desktop/mobile browser measurements, both themes and popup actions. Keep all emergency/approval safeguards.
