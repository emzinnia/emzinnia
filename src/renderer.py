"""Image renderer for the GitHub stats card."""

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from language_colors import GITHUB_LANGUAGE_COLORS

# Fallback colors for languages not in GitHub's palette
FALLBACK_LANGUAGE_COLORS = [
    "#e06c75", "#98c379", "#e5c07b", "#61afef", "#c678dd",
    "#56b6c2", "#be5046", "#d19a66", "#abb2bf", "#5c6370",
]


def get_language_color(language: str, fallback_index: int = 0) -> str:
    """Get the GitHub color for a language, with fallback for unknown languages."""
    # Try exact match first
    if language in GITHUB_LANGUAGE_COLORS:
        return GITHUB_LANGUAGE_COLORS[language]
    
    # Try case-insensitive match
    language_lower = language.lower()
    for lang, color in GITHUB_LANGUAGE_COLORS.items():
        if lang.lower() == language_lower:
            return color
    
    # Return a fallback color based on the index
    return FALLBACK_LANGUAGE_COLORS[fallback_index % len(FALLBACK_LANGUAGE_COLORS)]


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert hex color to RGBA tuple."""
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, alpha)


class StatsCardRenderer:
    """Renders the GitHub stats card as a PNG image."""

    # Base (1x) card dimensions. Actual output size is scaled by `self.scale`.
    BASE_CARD_WIDTH = 800
    BASE_CARD_HEIGHT = 400
    BASE_PADDING = 30
    BASE_CORNER_RADIUS = 20

    # Pokemon grid settings (New grid in bottom left box)
    POKEMON_GRID_COLS = 3
    POKEMON_GRID_ROWS = 2
    BASE_POKEMON_SPRITE_SIZE = 55
    BASE_POKEMON_SPACING = 5

    # Stats section settings
    BASE_STATS_START_X = 320  # Aligned with header box start (approx)
    BASE_LANGUAGE_BAR_WIDTH = 11
    BASE_LANGUAGE_BAR_HEIGHT = 201

    def __init__(self, theme: dict[str, str], scale: float = 2.0):
        self.theme = theme
        # Rendering scale multiplier. 2.0 => 1600x800 output while keeping the same layout.
        # Clamp to a sane minimum to avoid 0-sized assets if misconfigured.
        try:
            self.scale = float(scale)
        except (TypeError, ValueError):
            self.scale = 2.0
        if self.scale <= 0:
            self.scale = 2.0

        # Scaled dimensions
        self.CARD_WIDTH = self._s(self.BASE_CARD_WIDTH)
        self.CARD_HEIGHT = self._s(self.BASE_CARD_HEIGHT)
        self.PADDING = self._s(self.BASE_PADDING)
        self.CORNER_RADIUS = self._s(self.BASE_CORNER_RADIUS)

        self.POKEMON_SPRITE_SIZE = self._s(self.BASE_POKEMON_SPRITE_SIZE)
        self.POKEMON_SPACING = self._s(self.BASE_POKEMON_SPACING)

        self.STATS_START_X = self._s(self.BASE_STATS_START_X)
        self.LANGUAGE_BAR_WIDTH = self._s(self.BASE_LANGUAGE_BAR_WIDTH)
        self.LANGUAGE_BAR_HEIGHT = self._s(self.BASE_LANGUAGE_BAR_HEIGHT)

        self.bg_color = hex_to_rgba(theme.get("background", "#1a1b27"))
        self.text_color = hex_to_rgba(theme.get("text", "#c0caf5"))
        self.accent_color = hex_to_rgba(theme.get("accent", "#7aa2f7"))
        self.secondary_color = hex_to_rgba(theme.get("secondary", "#565f89"))
        self.star_color = hex_to_rgba(theme.get("star_color", "#e0af68"))
        self.commit_color = hex_to_rgba(theme.get("commit_color", "#9ece6a"))
        self.pr_color = hex_to_rgba(theme.get("pr_color", "#bb9af7"))
        self.issue_color = hex_to_rgba(theme.get("issue_color", "#f7768e"))
        self.contribution_color = hex_to_rgba(
            theme.get("contribution_color", "#7dcfff")
        )
        self.header_box_color = hex_to_rgba(theme.get("header_box", "#24283b"))
        self.team_box_color = hex_to_rgba(theme.get("team_box", "#24283b"))
        self.language_bar_border_color = hex_to_rgba(
            theme.get("language_bar_border", "#ffffff")
        )

        # Try to load a nice font, fallback to default
        self.title_font = self._load_font(self._s(28))
        self.header_font = self._load_font(self._s(20))
        self.body_font = self._load_font(self._s(16))
        self.small_font = self._load_font(self._s(14))
        self.greeting_font = self._load_font(self._s(18))
        self.username_font = self._load_font_bold(self._s(36))

    def _s(self, value: int | float) -> int:
        """Scale a value from base (1x) coordinate space to output pixels."""
        return int(round(float(value) * self.scale))

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load a font, with fallbacks."""
        # Get the assets directory relative to this file
        assets_dir = Path(__file__).parent / "assets"
        
        # Common font paths to try - Source Sans Pro preferred
        font_paths = [
            # Local assets folder (bundled with project)
            assets_dir / "SourceSans3-Regular.otf",
            # macOS - Source Sans Pro
            "/Library/Fonts/SourceSans3-Regular.otf",
            "/Library/Fonts/SourceSansPro-Regular.ttf",
            "/System/Library/Fonts/Supplemental/SourceSansPro-Regular.otf",
            # Linux - Source Sans Pro
            "/usr/share/fonts/truetype/source-sans-pro/SourceSansPro-Regular.ttf",
            "/usr/share/fonts/opentype/source-sans-pro/SourceSansPro-Regular.otf",
            # Windows - Source Sans Pro
            "C:/Windows/Fonts/SourceSansPro-Regular.ttf",
            # Fallbacks
            "/System/Library/Fonts/SFNSMono.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ]

        for font_path in font_paths:
            path = Path(font_path)
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size)
                except OSError:
                    continue

        # Fallback to default font
        return ImageFont.load_default()

    def _load_font_bold(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load a bold font, with fallbacks."""
        # Get the assets directory relative to this file
        assets_dir = Path(__file__).parent / "assets"
        
        # Bold font paths to try - Source Sans Pro Bold preferred
        font_paths = [
            # Local assets folder (bundled with project)
            assets_dir / "SourceSans3-Bold.otf",
            # macOS - Source Sans Pro Bold
            "/Library/Fonts/SourceSans3-Bold.otf",
            "/Library/Fonts/SourceSansPro-Bold.ttf",
            "/System/Library/Fonts/Supplemental/SourceSansPro-Bold.otf",
            # Linux - Source Sans Pro Bold
            "/usr/share/fonts/truetype/source-sans-pro/SourceSansPro-Bold.ttf",
            "/usr/share/fonts/opentype/source-sans-pro/SourceSansPro-Bold.otf",
            # Windows - Source Sans Pro Bold
            "C:/Windows/Fonts/SourceSansPro-Bold.ttf",
            # Fallbacks
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
        ]

        for font_path in font_paths:
            path = Path(font_path)
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size)
                except OSError:
                    continue

        # Fallback to regular font
        return self._load_font(size)

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[int, int, int, int],
        radius: int,
        fill: tuple[int, int, int, int],
    ) -> None:
        """Draw a rounded rectangle."""
        x1, y1, x2, y2 = xy

        # Draw the main rectangle
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)

        # Draw the four corners
        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
        draw.pieslice(
            [x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill
        )
        draw.pieslice(
            [x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill
        )
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

    def _draw_layout_containers(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw the structural layout containers."""
        # Header Box (Top Right)
        # Rect: x=236, y=24, width=555, height=84
        self._draw_rounded_rectangle(
            draw,
            (
                self._s(236),
                self._s(24),
                self._s(236 + 555),
                self._s(24 + 84),
            ),
            self._s(40),
            self.header_box_color,
        )

        # Speech Bubble Box (Bottom Left) - with tail pointing to profile image
        # Rect: x=22, y=209, width=200, height=169
        self._draw_speech_bubble(
            draw,
            (
                self._s(22),
                self._s(209),
                self._s(22 + 200),
                self._s(209 + 169),
            ),
            self._s(20),
            self.team_box_color,
        )

    def _draw_speech_bubble(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[int, int, int, int],
        radius: int,
        fill: tuple[int, int, int, int],
    ) -> None:
        """Draw a speech bubble body (without the tail - tail is drawn separately for z-ordering)."""
        # Draw only the main rounded rectangle body
        # The tail is drawn separately by _draw_speech_bubble_tail to appear above the profile image
        self._draw_rounded_rectangle(draw, xy, radius, fill)

    def _draw_speech_bubble_tail(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw the speech bubble tail on top of the profile image."""
        # Bubble box position: x=22, y=209, width=200, height=169
        y1 = self._s(209)  # Top of the bubble
        
        # Profile image is at x=122, y=101, size=100x100
        # Profile center bottom: (172, 201) in base coords
        # Bubble top is at y=209, so there's a small gap
        
        # Tail parameters - a nice curved speech bubble pointer
        tail_height = self._s(12)  # Height of the tail (connects to profile)
        
        # Position the tail to point toward the profile image center
        # Profile center is at x=172 (122 + 50), tail should point there
        tail_tip_x = self._s(172)  # Point directly at profile center
        tail_base_left = self._s(145)  # Left edge of tail base on bubble
        tail_base_right = self._s(195)  # Right edge of tail base on bubble
        
        # Create a curved tail using a polygon with extra points for smoothness
        # The tail emerges from the top of the bubble and curves toward the profile
        tail_points = [
            (tail_base_left, y1 + self._s(2)),  # Left base (slightly inside bubble for smooth join)
            (tail_tip_x - self._s(8), y1 - tail_height),  # Left of tip
            (tail_tip_x, y1 - tail_height - self._s(4)),  # Tip point
            (tail_tip_x + self._s(8), y1 - tail_height),  # Right of tip
            (tail_base_right, y1 + self._s(2)),  # Right base
        ]
        
        draw.polygon(tail_points, fill=self.team_box_color)

    def render(
        self,
        pokemon_sprites: list[Image.Image | None],
        stats: dict,
        output_path: str | Path,
        username: str = "Emzinnia",
        blurb_lines: list[str] | None = None,
        profile_image: Image.Image | None = None,
        labels: dict[str, str] | None = None,
    ) -> None:
        """
        Render the stats card to a PNG file.

        Args:
            pokemon_sprites: List of Pokemon sprite images (6 expected)
            stats: Dictionary containing total_stars, total_commits, total_prs,
                total_issues, contributions, languages
            output_path: Path to save the PNG file
            username: GitHub username to display in greeting
            profile_image: Optional profile image to display
            labels: Dictionary containing section labels (stats, languages)
        """
        # Create the base image
        image = Image.new("RGBA", (self.CARD_WIDTH, self.CARD_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw rounded background
        self._draw_rounded_rectangle(
            draw,
            (0, 0, self.CARD_WIDTH, self.CARD_HEIGHT),
            self.CORNER_RADIUS,
            self.bg_color,
        )

        # Draw layout containers
        self._draw_layout_containers(draw)

        # Draw Pokemon team in the header box (top right container)
        self._draw_team_header(image, pokemon_sprites)

        # Draw greeting section (below header box)
        self._draw_greeting(image, draw, username)

        # Draw profile image (below greeting, matching mockup position)
        if profile_image is not None:
            self._draw_profile_image(image, profile_image)

        # Draw speech bubble tail ON TOP of the profile image for proper z-ordering
        self._draw_speech_bubble_tail(draw)

        # Draw blurb section (bottom left container)
        self._draw_blurb_section(image, blurb_lines or [])

        # Draw stats section (right side)
        self._draw_stats_section(image, draw, stats, labels)

        # Draw etch lines in bottom-right corner
        self._draw_etch_lines(draw)

        # Draw border
        self._draw_border(draw)

        # Save the image
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, "PNG")
        print(f"Stats card saved to {output_path}")

    def _draw_multicolor_text(
        self,
        image: Image.Image,
        x: int,
        y: int,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> int:
        """Draw text with a rainbow gradient effect. Returns the width of the text."""
        # Rainbow gradient colors
        gradient_colors = [
            "#ff6b6b",  # Red
            "#ffa94d",  # Orange
            "#ffd43b",  # Yellow
            "#69db7c",  # Green
            "#4dabf7",  # Blue
            "#9775fa",  # Purple
            "#f783ac",  # Pink
        ]

        draw = ImageDraw.Draw(image)
        current_x = x
        total_width = 0

        for i, char in enumerate(text):
            # Cycle through gradient colors
            color_idx = i % len(gradient_colors)
            color = hex_to_rgba(gradient_colors[color_idx])

            # Draw the character
            draw.text((current_x, y), char, font=font, fill=color)

            # Get character width and move to next position
            bbox = draw.textbbox((0, 0), char, font=font)
            char_width = bbox[2] - bbox[0]
            current_x += char_width
            total_width += char_width

        return total_width

    def _draw_greeting(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        username: str,
    ) -> None:
        """Draw the greeting section with 'Hi, I'm' and multicolor username."""
        # Position in top left, matching mockup (x=36, y=25 in base coords)
        x = self._s(36)
        y = self._s(25)

        # Draw "Hi, I'm"
        draw.text(
            (x, y),
            "hello, i'm",
            font=self.greeting_font,
            fill=self.text_color,
        )
        y += self._s(28)

        # Draw username in multicolor
        self._draw_multicolor_text(image, x, y, username, self.username_font)

    def _draw_profile_image(
        self,
        image: Image.Image,
        profile_image: Image.Image,
    ) -> None:
        """Draw the profile image with rounded corners, matching mockup position."""
        # Mockup position: x=122, y=101, size=100x100, corner radius=23
        x = self._s(122)
        y = self._s(101)
        size = self._s(100)
        corner_radius = self._s(23)

        # Resize profile image to target size
        profile = profile_image.convert("RGBA")
        profile = profile.resize((size, size), Image.Resampling.LANCZOS)

        # Create rounded corner mask
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [0, 0, size, size],
            radius=corner_radius,
            fill=255
        )

        # Apply the rounded mask to the profile image
        profile.putalpha(mask)

        # Paste onto the main image
        image.paste(profile, (x, y), profile)

    def _wrap_text_to_width(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        """Wrap a single string into multiple lines that fit within max_width."""
        text = (text or "").strip()
        if not text:
            return []

        words = text.split()
        lines: list[str] = []
        current = ""

        for w in words:
            candidate = f"{current} {w}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = w
            else:
                # Extremely long single word: hard-break it.
                lines.append(w)
                current = ""

        if current:
            lines.append(current)

        return lines

    def _wrap_text_balanced(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        """Wrap text aiming for balanced line lengths that stay within max_width."""
        text = (text or "").strip()
        if not text:
            return []

        words = text.split()
        if not words:
            return []

        # If a single word already exceeds the max width, fall back to greedy wrapping.
        for word in words:
            bbox = draw.textbbox((0, 0), word, font=font)
            if (bbox[2] - bbox[0]) > max_width:
                return self._wrap_text_to_width(draw, text, font, max_width)

        n = len(words)
        widths_cache: dict[tuple[int, int], int] = {}

        def line_width(i: int, j: int) -> int:
            key = (i, j)
            if key not in widths_cache:
                segment = " ".join(words[i:j])
                bbox = draw.textbbox((0, 0), segment, font=font)
                widths_cache[key] = bbox[2] - bbox[0]
            return widths_cache[key]

        # Dynamic programming to minimize the raggedness between lines.
        inf = 10**18
        cost = [inf] * (n + 1)
        breaks = [n] * n
        cost[n] = 0

        for i in range(n - 1, -1, -1):
            for j in range(i + 1, n + 1):
                width = line_width(i, j)
                if width > max_width:
                    break
                remaining = max_width - width
                penalty = remaining * remaining
                total = penalty + cost[j]
                if total < cost[i]:
                    cost[i] = total
                    breaks[i] = j

        # If we failed to find a layout, fall back to the greedy wrapper.
        if cost[0] >= inf:
            return self._wrap_text_to_width(draw, text, font, max_width)

        lines: list[str] = []
        idx = 0
        while idx < n:
            nxt = breaks[idx]
            if nxt <= idx:
                break
            lines.append(" ".join(words[idx:nxt]))
            idx = nxt

        return lines or self._wrap_text_to_width(draw, text, font, max_width)

    def _draw_team_header(self, image: Image.Image, sprites: list[Image.Image | None]) -> None:
        """Draw the Pokemon team row inside the header box (top right container)."""
        # Header container: x=236, y=24, w=555, h=84
        container_x = self._s(236)
        container_y = self._s(24)
        container_w = self._s(555)
        container_h = self._s(84)

        draw = ImageDraw.Draw(image)

        pad_x = self._s(24)
        # Sprites row, centered within the header container
        start_x = container_x + pad_x
        available_w = container_w - (2 * pad_x)

        team = [s for s in (sprites or [])[:6] if s is not None]
        if not team or available_w <= 0:
            return

        spacing = max(self._s(4), self.POKEMON_SPACING)
        sprite_size = self.POKEMON_SPRITE_SIZE

        total_needed = len(team) * sprite_size + (len(team) - 1) * spacing
        if total_needed > available_w:
            sprite_size = max(
                self._s(20),
                int((available_w - (len(team) - 1) * spacing) / max(1, len(team))),
            )
            total_needed = len(team) * sprite_size + (len(team) - 1) * spacing

        sprite_y = container_y + (container_h - sprite_size) // 2
        if total_needed < available_w:
            start_x = start_x + (available_w - total_needed) // 2

        for i, sprite in enumerate(team):
            x = start_x + i * (sprite_size + spacing)
            if x + sprite_size > container_x + container_w - pad_x:
                break

            if sprite.size != (sprite_size, sprite_size):
                sprite = sprite.resize((sprite_size, sprite_size), Image.Resampling.NEAREST)

            image.paste(sprite, (x, sprite_y), sprite)

    def _calculate_blurb_height(
        self,
        draw: ImageDraw.ImageDraw,
        blurb_lines: list[str],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_w: int,
        line_gap: int,
        para_gap: int,
    ) -> int:
        """Calculate the total height needed to render blurb text with given font."""
        total_height = 0
        for idx, para in enumerate(blurb_lines):
            wrapped = self._wrap_text_balanced(draw, str(para), font, max_w)
            for line in wrapped:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_h = bbox[3] - bbox[1]
                total_height += line_h + line_gap
            # Remove the last line_gap and add para_gap between paragraphs
            if wrapped:
                total_height -= line_gap
            if idx < len(blurb_lines) - 1:
                total_height += para_gap
        return total_height

    def _find_optimal_blurb_font_size(
        self,
        draw: ImageDraw.ImageDraw,
        blurb_lines: list[str],
        max_w: int,
        max_h: int,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Find the largest font size that fits the blurb text in the available space."""
        # Font size range (in base coordinates, before scaling)
        min_size = 10
        max_size = 24
        
        best_font = self._load_font(self._s(min_size))
        
        for base_size in range(max_size, min_size - 1, -1):
            font = self._load_font(self._s(base_size))
            line_gap = self._s(4)
            para_gap = self._s(8)
            
            total_height = self._calculate_blurb_height(
                draw, blurb_lines, font, max_w, line_gap, para_gap
            )
            
            if total_height <= max_h:
                return font
        
        return best_font

    def _draw_blurb_section(self, image: Image.Image, blurb_lines: list[str]) -> None:
        """Draw the blurb text in the bottom-left container (previously the team box)."""
        # Bottom-left container: x=22, y=209, w=200, h=169
        container_x = self._s(22)
        container_y = self._s(209)
        container_w = self._s(200)
        container_h = self._s(169)

        draw = ImageDraw.Draw(image)

        pad = self._s(20)
        x = container_x + pad
        y = container_y + pad
        max_w = container_w - 2 * pad
        max_h = container_h - 2 * pad

        if not blurb_lines:
            return

        # Find the optimal font size that fills the available space
        font = self._find_optimal_blurb_font_size(draw, blurb_lines, max_w, max_h)
        line_gap = self._s(4)
        para_gap = self._s(8)

        for idx, para in enumerate(blurb_lines):
            wrapped = self._wrap_text_balanced(draw, str(para), font, max_w)
            for line in wrapped:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_h = bbox[3] - bbox[1]
                draw.text((x, y), line, font=font, fill=self.text_color)
                y += (line_h + line_gap)
            # Remove extra line_gap and add para_gap between paragraphs
            if wrapped:
                y -= line_gap
            if idx < len(blurb_lines) - 1:
                y += para_gap

    def _draw_star_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
        """Draw a 5-pointed star icon centered at (cx, cy)."""
        import math
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)  # Start from top
            r = size if i % 2 == 0 else size * 0.4
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(points, fill=color)

    def _draw_commit_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
        """Draw a git commit icon (circle with lines) centered at (cx, cy)."""
        line_width = max(2, self._s(2))
        # Vertical lines above and below
        draw.line([(cx, cy - size), (cx, cy - size // 3)], fill=color, width=line_width)
        draw.line([(cx, cy + size // 3), (cx, cy + size)], fill=color, width=line_width)
        # Circle in middle
        r = size // 3
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=line_width)

    def _draw_pr_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
        """Draw a git pull request / merge icon centered at (cx, cy)."""
        line_width = max(2, self._s(2))
        r = size // 4
        offset = size // 2
        # Left side: top circle, vertical line, bottom circle
        left_x = cx - offset
        draw.ellipse([left_x - r, cy - size + r, left_x + r, cy - size + r * 3], outline=color, width=line_width)
        draw.line([(left_x, cy - size + r * 3), (left_x, cy + size - r * 3)], fill=color, width=line_width)
        draw.ellipse([left_x - r, cy + size - r * 3, left_x + r, cy + size - r], outline=color, width=line_width)
        # Center vertical line
        draw.line([(cx, cy - size), (cx, cy + size)], fill=color, width=line_width)
        # Right side: top circle with curve merging to center
        right_x = cx + offset
        draw.ellipse([right_x - r, cy - size + r, right_x + r, cy - size + r * 3], outline=color, width=line_width)
        # Curved line from right to center (approximate with arc)
        draw.arc([cx - offset, cy - size + r * 3, right_x, cy], 270, 360, fill=color, width=line_width)

    def _draw_issue_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
        """Draw a circle with exclamation mark (issue/alert icon) centered at (cx, cy)."""
        line_width = max(2, self._s(2))
        # Outer circle
        draw.ellipse([cx - size, cy - size, cx + size, cy + size], outline=color, width=line_width)
        # Exclamation mark: vertical line and dot
        excl_top = cy - size // 2
        excl_bottom = cy + size // 4
        dot_y = cy + size // 2
        draw.line([(cx, excl_top), (cx, excl_bottom)], fill=color, width=line_width)
        # Dot at bottom
        dot_r = max(2, size // 6)
        draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=color)

    def _draw_contribution_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple) -> None:
        """Draw a book/document icon (contribution symbol) centered at (cx, cy)."""
        line_width = max(2, self._s(2))
        w = int(size * 0.8)
        h = size
        # Book spine and pages
        # Left edge (spine)
        draw.line([(cx - w, cy - h), (cx - w, cy + h)], fill=color, width=line_width)
        # Top edge
        draw.line([(cx - w, cy - h), (cx + w, cy - h)], fill=color, width=line_width)
        # Right edge
        draw.line([(cx + w, cy - h), (cx + w, cy + h)], fill=color, width=line_width)
        # Bottom curve (like a book)
        draw.arc([cx - w - size // 4, cy + h - size // 2, cx + w, cy + h + size // 2], 0, 90, fill=color, width=line_width)
        draw.line([(cx - w, cy + h), (cx - w + size // 4, cy + h)], fill=color, width=line_width)
        # Inner page lines
        line_y1 = cy - h // 2
        line_y2 = cy
        line_y3 = cy + h // 2
        draw.line([(cx - w // 2, line_y1), (cx + w // 2, line_y1)], fill=color, width=max(1, line_width // 2))
        draw.line([(cx - w // 2, line_y2), (cx + w // 2, line_y2)], fill=color, width=max(1, line_width // 2))
        draw.line([(cx - w // 2, line_y3), (cx + w // 2, line_y3)], fill=color, width=max(1, line_width // 2))

    def _draw_stats_section(self, image: Image.Image, draw: ImageDraw.ImageDraw, stats: dict, labels: dict | None = None) -> None:
        """Draw the stats section on the right side."""
        # Stats text area: Left of vertical bar (290 to 558)
        # Vertical bar: x=558
        
        labels = labels or {}
        stats_label = labels.get("stats", "stats")
        languages_label = labels.get("languages", "languages")
        
        x = self._s(290)
        label_y = self._s(140)  # Section labels positioned above content
        
        # Draw "stats" section label
        draw.text(
            (x, label_y),
            stats_label,
            font=self.body_font,
            fill=self.secondary_color,
        )
        
        y = self._s(180)  # Stats items start below section label

        # Icon settings
        icon_size = self._s(10)
        icon_x = x + icon_size  # Center point for icons
        text_x = x + self._s(30)  # Text starts after icon
        row_height = self._s(36)  # Spacing between rows

        # Stats items in column layout: icon, value, label
        stats_items = [
            (self._draw_star_icon, stats.get("total_stars", 0), "total stars", self.star_color),
            (
                self._draw_commit_icon,
                stats.get("total_commits", stats.get("commits_this_year", 0)),
                "total commits",
                self.commit_color,
            ),
            (self._draw_pr_icon, stats.get("total_prs", 0), "total PRs", self.pr_color),
            (self._draw_issue_icon, stats.get("total_issues", 0), "total issues", self.issue_color),
            (self._draw_contribution_icon, stats.get("contributions", 0), "contributions", self.contribution_color),
        ]

        for i, (icon_func, value, label, color) in enumerate(stats_items):
            item_y = y + i * row_height
            icon_cy = item_y + self._s(8)  # Center icon vertically with text
            
            # Draw the icon
            icon_func(draw, icon_x, icon_cy, icon_size, color)
            
            # Draw value and label on same line
            text = f"{value:,} {label}"
            draw.text(
                (text_x, item_y),
                text,
                font=self.body_font,
                fill=self.text_color,
            )

        # Vertical Bar for Languages
        # x=558, y=177, w=11, h=201
        bar_x = self._s(558)
        bar_y = self._s(180)  # Bar starts below label
        bar_w = self._s(11)
        bar_h = self._s(164)
        
        languages: list[tuple[str, float]] = stats.get("languages", []) or []
        excluded_languages: list[str] = stats.get("excluded_languages", []) or []
        if excluded_languages:
            languages = self._filter_languages(languages, excluded_languages)
            
        if languages:
            # Draw "languages" section label ABOVE the bar
            draw.text(
                (bar_x + self._s(30), label_y),
                languages_label,
                font=self.body_font,
                fill=self.secondary_color,
            )
            
            # Draw vertical stacked bar
            scale_bars = stats.get("scale_language_bars", True)
            use_gradient = stats.get("language_gradient", True)
            show_border = stats.get("language_bar_border", False)
            self._draw_vertical_language_bar(image, draw, bar_x, bar_y, bar_w, bar_h, languages, scale_bars, use_gradient, show_border)
            
            # Draw language legend to the right of the bar
            self._draw_vertical_language_legend(draw, bar_x + self._s(30), bar_y, bar_h, languages)

    def _draw_vertical_language_bar(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        languages: list[tuple[str, float]],
        scale_bars: bool = True,
        use_gradient: bool = True,
        show_border: bool = False,
    ) -> None:
        """Draw a vertical stacked bar for languages.
        
        Args:
            scale_bars: If True, segment sizes are proportional to language percentage.
                       If False, each language gets equal space in the bar.
            use_gradient: If True, draw smooth gradient transitions between colors.
                         If False, draw solid color blocks with no blending.
            show_border: If True, draw a border around the language bar.
        """
        # Background
        draw.rounded_rectangle(
            [x, y, x + w, y + h],
            radius=max(1, w // 2),
            fill=self.secondary_color
        )
        
        visible_languages = languages[:5]
        if not visible_languages:
            return
        
        total_pct = sum(pct for _, pct in visible_languages)
        if total_pct == 0:
            return

        # Off-screen surface so we can apply a rounded mask to the fill
        bar_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        bar_draw = ImageDraw.Draw(bar_img)

        # Calculate segment boundaries and colors
        segments: list[tuple[int, int, tuple[int, int, int, int]]] = []
        current_y = 0
        num_languages = len(visible_languages)
        
        for i, (lang, percentage) in enumerate(visible_languages):
            if scale_bars:
                # Proportional to actual percentage
                segment_height = int((percentage / total_pct) * h)
            else:
                # Equal distribution for each language
                segment_height = h // num_languages
                # Give any remainder pixels to the last segment
                if i == num_languages - 1:
                    segment_height = h - current_y
            
            if segment_height < 1:
                continue
            
            color = hex_to_rgba(get_language_color(lang, i))
            segments.append((current_y, current_y + segment_height, color))
            current_y += segment_height
        
        if not segments:
            return
        
        if use_gradient:
            # Size of gradient transition zone between segments (half on each side of boundary)
            gradient_size = self._s(8)
            
            # Draw each row with gradient blending at transitions
            for row_y in range(0, h):
                # Find which segment(s) this row belongs to
                row_color = None
                
                for seg_idx, (seg_start, seg_end, seg_color) in enumerate(segments):
                    if seg_start <= row_y < seg_end:
                        # Check if we're in a transition zone FROM the previous segment
                        if seg_idx > 0:
                            _, _, prev_color = segments[seg_idx - 1]
                            dist_from_prev = row_y - seg_start
                            
                            if dist_from_prev < gradient_size:
                                # Blend with previous segment's color (fading out)
                                blend_factor = dist_from_prev / gradient_size
                                row_color = self._blend_colors(prev_color, seg_color, blend_factor)
                                break
                        
                        # Check if we're in a transition zone TO the next segment
                        if seg_idx < len(segments) - 1:
                            next_seg_start, _, next_color = segments[seg_idx + 1]
                            dist_to_next = next_seg_start - row_y
                            
                            if dist_to_next <= gradient_size:
                                # Blend with next segment's color (fading in)
                                blend_factor = 1.0 - (dist_to_next / gradient_size)
                                row_color = self._blend_colors(seg_color, next_color, blend_factor)
                                break
                        
                        row_color = seg_color
                        break
                
                if row_color is None:
                    # Fallback to last segment color
                    row_color = segments[-1][2] if segments else self.secondary_color
                
                # Draw the row
                bar_draw.line([(0, row_y), (w, row_y)], fill=row_color)
        else:
            # Draw solid color blocks without gradient blending
            for seg_start, seg_end, seg_color in segments:
                bar_draw.rectangle([0, seg_start, w, seg_end], fill=seg_color)

        # Clip the stacked fill to a rounded mask for pill-like ends
        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [0, 0, w, h],
            radius=max(1, w // 2),
            fill=255,
        )
        bar_img.putalpha(mask)
        image.paste(bar_img, (x, y), bar_img)
        
        # Draw border around the bar if enabled
        if show_border:
            border_width = max(1, self._s(1))
            draw.rounded_rectangle(
                [x, y, x + w, y + h],
                radius=max(1, w // 2),
                outline=self.language_bar_border_color,
                width=border_width,
            )
    
    def _blend_colors(
        self,
        color1: tuple[int, int, int, int],
        color2: tuple[int, int, int, int],
        factor: float,
    ) -> tuple[int, int, int, int]:
        """Blend two RGBA colors. factor=0 returns color1, factor=1 returns color2."""
        factor = max(0.0, min(1.0, factor))
        return (
            int(color1[0] + (color2[0] - color1[0]) * factor),
            int(color1[1] + (color2[1] - color1[1]) * factor),
            int(color1[2] + (color2[2] - color1[2]) * factor),
            int(color1[3] + (color2[3] - color1[3]) * factor),
        )

    def _draw_vertical_language_legend(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        bar_height: int,
        languages: list[tuple[str, float]],
    ) -> None:
        """Draw language legend to the right of the bar."""
        row_height = self._s(36)
        visible_languages = languages[:5]
        
        # Top-align with the stats items
        current_y = y
        for i, (lang, percentage) in enumerate(visible_languages):
            # Use GitHub's official language color
            color = hex_to_rgba(get_language_color(lang, i))
            
            # Calculate text metrics for proper vertical centering
            lang_bbox = draw.textbbox((0, 0), lang, font=self.body_font)
            lang_text_height = lang_bbox[3] - lang_bbox[1]
            pct_text = f"{percentage}%"
            pct_bbox = draw.textbbox((0, 0), pct_text, font=self.small_font)
            pct_text_height = pct_bbox[3] - pct_bbox[1]
            
            # Use the taller of the two text elements as the reference height
            text_height = max(lang_text_height, pct_text_height)
            
            # Dot size
            dot_size = self._s(10)
            
            # Calculate vertical center of this row
            row_center_y = current_y + text_height // 2
            
            # Draw dot centered vertically
            dot_y = row_center_y - dot_size // 2
            draw.ellipse(
                [x, dot_y, x + dot_size, dot_y + dot_size],
                fill=color,
            )
            
            # Draw language name centered vertically
            text_x = x + self._s(20)
            lang_y = row_center_y - lang_text_height // 2
            draw.text(
                (text_x, lang_y),
                lang,
                font=self.body_font,
                fill=self.text_color
            )
            
            # Draw percentage centered vertically, to the right of language name
            lang_width = lang_bbox[2] - lang_bbox[0]
            pct_y = row_center_y - pct_text_height // 2
            draw.text(
                (text_x + lang_width + self._s(8), pct_y),
                pct_text,
                font=self.small_font,
                fill=self.secondary_color
            )
            
            current_y += row_height

    def _normalize_language_name(self, name: str) -> str:
        """Normalize a language name for case-insensitive matching."""
        return (name or "").strip().casefold()

    def _filter_languages(
        self, languages: list[tuple[str, float]], excluded: list[str]
    ) -> list[tuple[str, float]]:
        """Remove excluded languages from the language list (case-insensitive)."""
        excluded_set = {self._normalize_language_name(x) for x in excluded if x}
        if not excluded_set:
            return languages
        return [
            (lang, pct)
            for (lang, pct) in languages
            if self._normalize_language_name(lang) not in excluded_set
        ]

    def _draw_border(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw a subtle border around the card."""
        border_color = hex_to_rgba(self.theme.get("accent", "#7aa2f7"), 80)
        border_width = max(1, self._s(2))

        # Draw border lines
        draw.rounded_rectangle(
            [0, 0, self.CARD_WIDTH - 1, self.CARD_HEIGHT - 1],
            radius=self.CORNER_RADIUS,
            outline=border_color,
            width=border_width,
        )

    def _draw_etch_lines(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw decorative diagonal etch lines in the bottom-right corner."""
        # Etch line color: light gray with 70% opacity
        etch_color = hex_to_rgba("#E5E5E5", int(255 * 0.7))
        line_width = max(1, self._s(1))

        # Three diagonal lines from mockup coordinates (base 800x400 card)
        # Line 1 (shortest, closest to corner): (791.375, 369.331) to (776.375, 386.331)
        # Line 2 (medium): (791.367, 359.34) to (766.367, 386.34)
        # Line 3 (longest): (791.354, 349.354) to (754.354, 386.354)
        etch_lines = [
            ((791.375, 369.331), (776.375, 386.331)),
            ((791.367, 359.34), (766.367, 386.34)),
            ((791.354, 349.354), (754.354, 386.354)),
        ]

        for (x1, y1), (x2, y2) in etch_lines:
            draw.line(
                [(self._s(x1), self._s(y1)), (self._s(x2), self._s(y2))],
                fill=etch_color,
                width=line_width,
            )
