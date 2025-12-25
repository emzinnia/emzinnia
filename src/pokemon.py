"""PokeAPI client for fetching Pokemon sprites."""

from io import BytesIO

import requests
from PIL import Image


class PokemonFetcher:
    """Fetches Pokemon sprites from PokeAPI."""

    API_URL = "https://pokeapi.co/api/v2/pokemon"

    def __init__(self):
        self.session = requests.Session()
        self.sprite_cache: dict[str, Image.Image] = {}

    def get_pokemon_sprite(self, pokemon_name: str, shiny: bool = False) -> Image.Image | None:
        """
        Fetch a Pokemon's sprite image.

        Args:
            pokemon_name: The name of the Pokemon (lowercase)
            shiny: Whether to fetch the shiny sprite variant

        Returns:
            PIL Image of the Pokemon sprite, or None if not found
        """
        pokemon_name = pokemon_name.lower().strip()
        cache_key = f"{pokemon_name}_shiny" if shiny else pokemon_name

        # Check cache first
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key].copy()

        try:
            # Get Pokemon data from PokeAPI
            response = self.session.get(
                f"{self.API_URL}/{pokemon_name}",
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # Get the game sprite (pixel art style)
            sprites = data.get("sprites", {})
            sprite_key = "front_shiny" if shiny else "front_default"
            sprite_url = sprites.get(sprite_key)

            if not sprite_url:
                print(f"No {'shiny ' if shiny else ''}sprite found for {pokemon_name}")
                return None

            # Download the sprite image
            sprite_response = self.session.get(sprite_url, timeout=30)
            sprite_response.raise_for_status()

            # Convert to PIL Image
            image = Image.open(BytesIO(sprite_response.content))

            # Convert to RGBA if not already
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Cache the sprite
            self.sprite_cache[cache_key] = image.copy()

            return image

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Pokemon {pokemon_name}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error for {pokemon_name}: {e}")
            return None

    def get_team_sprites(
        self, team: list[str | dict], sprite_size: tuple[int, int] = (96, 96)
    ) -> list[Image.Image | None]:
        """
        Fetch sprites for a team of Pokemon.

        Args:
            team: List of Pokemon names (strings) or dicts with 'name' and optional 'shiny' keys
            sprite_size: Size to resize sprites to (width, height)

        Returns:
            List of PIL Images (or None for failed fetches)
        """
        sprites = []

        for pokemon in team:
            # Support both string format and dict format with shiny option
            if isinstance(pokemon, dict):
                pokemon_name = pokemon.get("name", "")
                shiny = pokemon.get("shiny", False)
            else:
                pokemon_name = pokemon
                shiny = False

            sprite = self.get_pokemon_sprite(pokemon_name, shiny=shiny)

            if sprite:
                # Scale up pixel art using nearest neighbor to preserve crisp pixels
                # Game sprites are typically 96x96, scale to target size
                scale_factor = min(sprite_size[0] / sprite.width, sprite_size[1] / sprite.height)
                new_width = int(sprite.width * scale_factor)
                new_height = int(sprite.height * scale_factor)
                
                sprite = sprite.resize(
                    (new_width, new_height),
                    Image.Resampling.NEAREST  # Preserve pixel art look
                )

                # Create a new image with the exact size and paste the sprite centered
                new_sprite = Image.new("RGBA", sprite_size, (0, 0, 0, 0))
                offset = (
                    (sprite_size[0] - sprite.width) // 2,
                    (sprite_size[1] - sprite.height) // 2,
                )
                new_sprite.paste(sprite, offset, sprite)
                sprites.append(new_sprite)
            else:
                # Create a placeholder for missing sprites
                placeholder = Image.new("RGBA", sprite_size, (128, 128, 128, 100))
                sprites.append(placeholder)

        return sprites

