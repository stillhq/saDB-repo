Here is the criteria for the stillRating system

Warning:
- Against Terms of Service for a third party client
- Broken on Wayland
- Abandoned
- Security issues (but still required in work flows, otherwise would be rejected)
  - Emulators / Torrent Clients
    - Emulator Warning:
      Emulators allow running software designed for other systems.
      Use emulators responsibly and only to play games you legally own. Downloading
      or distributing copyrighted ROMs without permission is illegal. Users are responsible
      for complying with all applicable laws when using emulators.
    - Torrent Warning:
      ****Torrent clients allow peer-to-peer file sharing over decentralized
      networks. Use torrents responsibly and only to download or share content you have permission for.
      Downloading or distributing copyrighted material without authorization is illegal.
      Users are responsible for complying with all applicable laws when using torrent software.****

Bronze:
- Qt (without hard coded theme)
- Theming issues
- Major flatpak container issues
- Inconsistent with GNOME Human Interface Guidelines (GTK only)

Silver:
- Gtk2
- Qt (hard coded theme), Election, or other non Gtk app without theming issues
  - Exception for games, and some apps met to be used in full screen such as Kodi
- Minor flatpak container issues
- Partial adherence to GNOME HIG (GTK Only)
- Dark mode support
- Regular updates and active maintenance


Gold:
- Gtk3, Gtk4, Libadwaita
- Sandboxed with Flatpak and proper portal usage


Gold Plus:
- Libadwaita
- Full GNOME integration (e.g., search provider, settings)
- Adaptive