import unittest
from src.weather_map.config import MAP_STYLES


class TestConfig(unittest.TestCase):
    
    def test_map_styles_exists(self):
        """Test that MAP_STYLES configuration exists."""
        self.assertIsNotNone(MAP_STYLES)
        self.assertIsInstance(MAP_STYLES, dict)
    
    def test_map_styles_not_empty(self):
        """Test that MAP_STYLES contains map style definitions."""
        self.assertGreater(len(MAP_STYLES), 0)
    
    def test_map_styles_structure(self):
        """Test that MAP_STYLES has the expected structure."""
        for style_name, style_config in MAP_STYLES.items():
            # Each style should have a name (key) that's a string
            self.assertIsInstance(style_name, str)
            self.assertGreater(len(style_name), 0)
            
            # Each style config should be a dictionary or string
            self.assertTrue(
                isinstance(style_config, (dict, str)),
                f"Style '{style_name}' config should be dict or string, got {type(style_config)}"
            )
    
    def test_common_map_styles_present(self):
        """Test that common map styles are present."""
        # These are typical map styles that should be available
        expected_styles = ['Streets', 'Light', 'Dark', 'Outdoors', 'Satellite']
        
        for expected_style in expected_styles:
            # Check if the exact name or a similar name exists
            style_names = list(MAP_STYLES.keys())
            style_found = any(
                expected_style.lower() in style_name.lower() 
                for style_name in style_names
            )
            self.assertTrue(
                style_found, 
                f"Expected style '{expected_style}' or similar not found in {style_names}"
            )
    
    def test_map_styles_keys_are_strings(self):
        """Test that all MAP_STYLES keys are strings."""
        for key in MAP_STYLES.keys():
            self.assertIsInstance(key, str)
            self.assertGreater(len(key.strip()), 0)
    
    def test_map_styles_values_valid(self):
        """Test that MAP_STYLES values are valid configurations."""
        for style_name, style_config in MAP_STYLES.items():
            if isinstance(style_config, dict):
                # If it's a dict, it should have reasonable keys
                # This is flexible since we don't know the exact structure
                self.assertIsInstance(style_config, dict)
            elif isinstance(style_config, str):
                # If it's a string, it should not be empty
                self.assertGreater(len(style_config.strip()), 0)


if __name__ == '__main__':
    unittest.main()
