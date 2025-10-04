#!/usr/bin/env python3
"""
@file
@brief YouTube Timestamps to CUE File Converter

Parses timestamped track listings (e.g., from YouTube video descriptions)
and generates a valid CUE sheet for audio players.
"""

import re
import os
import sys
from pathlib import Path
from datetime import datetime


class CueGenerator:
    """
    @class CueGenerator
    @brief Handles parsing timestamps, metadata collection, and CUE file generation.
    """

    def __init__(self):
        """@brief Initialize default metadata and track storage."""
        self.album = ""
        self.artist = ""
        self.year = ""
        self.genre = ""
        self.audio_file = ""
        self.tracks = []
    
    def parse_timestamp(self, timestamp):
        """
        @brief Convert a timestamp string into minutes, seconds, and frames.

        Supports the following formats:
        - `MM:SS`
        - `HH:MM:SS`

        Frames are set to zero because typical YouTube timestamps do not include sub-second values.

        @param timestamp A string representing the timestamp.
        @return (minutes, seconds, frames) as integers.
        @raises ValueError if the timestamp is not in a recognized format.
        """
        timestamp = timestamp.strip()
        parts = timestamp.split(':')

        if len(parts) == 2:         # MM:SS
            minutes = int(parts[0])
            seconds = int(parts[1])
        elif len(parts) == 3:       # HH:MM:SS
            hours = int(parts[0])
            minutes = int(parts[1]) + (hours * 60)
            seconds = int(parts[2])
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}")
        
        frames = 0  # CUE sheets use 75 frames/second; default to 0
        return minutes, seconds, frames
    
    def parse_timestamp_line(self, line):
        """
        @brief Extract timestamp and track title from a single line of text.

        Supports common YouTube timestamp formats such as:
        - `"0:00 Intro"`
        - `"[0:00] Intro"`
        - `"Intro (0:00)"`

        @param line A single line from the timestamps file.
        @return A dict with keys `timestamp` and `title` if matched; otherwise `None`.
        """
        line = line.strip()
        if not line:
            return None
        
        # Remove simple list prefixes like "1. "
        line = re.sub(r'^[\d]+\.\s*', '', line)
        
        patterns = [
            r'^[\[\(]?(\d{1,2}:\d{2}(?::\d{2})?)[\]\)]?\s+(.+)$',
            r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$',
            r'^(.+?)\s+[\[\(]?(\d{1,2}:\d{2}(?::\d{2})?)[\]\)]?$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                g = match.groups()
                if ':' in g[0]:
                    timestamp, title = g[0], g[1]
                else:
                    title, timestamp = g[0], g[1]
                
                return {'timestamp': timestamp.strip(), 'title': title.strip()}
        
        return None
    
    def read_timestamps_file(self, filepath):
        """
        @brief Load and parse a text file containing timestamped track listings.

        @param filepath Path to the text file.
        @return Number of tracks successfully parsed.
        @raises FileNotFoundError if the file cannot be opened.
        @raises ValueError if no valid timestamps are found.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            tracks = []
            for line_num, line in enumerate(lines, 1):
                parsed = self.parse_timestamp_line(line)
                if parsed:
                    try:
                        mins, secs, frames = self.parse_timestamp(parsed['timestamp'])
                        tracks.append({
                            'title': parsed['title'],
                            'minutes': mins,
                            'seconds': secs,
                            'frames': frames
                        })
                    except ValueError as e:
                        print(f"Warning: Skipping line {line_num} - {e}")
            
            if not tracks:
                raise ValueError("No valid timestamps found in file")
            
            self.tracks = tracks
            return len(tracks)
        
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")
        except Exception as e:
            raise Exception(f"Error reading file: {e}")
    
    def get_user_input(self):
        """
        @brief Prompt the user for album metadata and audio file details.

        If the user skips a field, a reasonable default is assigned.
        """
        print("\n" + "="*60)
        print("CUE FILE METADATA")
        print("="*60)
        
        self.artist = input("Enter Artist/Performer name: ").strip() or "Unknown Artist"
        self.album = input("Enter Album/Mix name: ").strip() or "Unknown Album"
        self.audio_file = input("Enter audio filename (e.g., audio.mp3): ").strip() or "audio.wav"
        
        year_input = input("Enter year (optional, press Enter to skip): ").strip()
        if year_input.isdigit():
            self.year = year_input
        
        self.genre = input("Enter genre (optional, press Enter to skip): ").strip()
        print("\n" + "="*60)
    
    def review_tracks(self):
        """
        @brief Display parsed tracks for user confirmation.

        @return True if the user accepts the parsed list; False otherwise.
        """
        print("\nPARSED TRACKS:")
        print("="*60)
        for i, track in enumerate(self.tracks, 1):
            timestamp = f"{track['minutes']:02d}:{track['seconds']:02d}:{track['frames']:02d}"
            print(f"{i:2d}. [{timestamp}] {track['title']}")
        print("="*60)
        
        response = input("\nDo these tracks look correct? (y/n): ").strip().lower()
        return response in ('y', 'yes', '')
    
    def generate_cue_content(self):
        """
        @brief Construct the text of the CUE sheet.

        @return A string containing the entire CUE sheet content.
        """
        cue_lines = []
        
        cue_lines.append(f'REM GENRE "{self.genre}"' if self.genre else 'REM GENRE "Unknown"')
        cue_lines.append(f'REM DATE {self.year}' if self.year else f'REM DATE {datetime.now().year}')
        cue_lines.append('REM COMMENT "Generated by YouTube to CUE Converter"')
        
        cue_lines.append(f'PERFORMER "{self.artist}"')
        cue_lines.append(f'TITLE "{self.album}"')
        cue_lines.append(f'FILE "{self.audio_file}" WAVE')
        
        for i, track in enumerate(self.tracks, 1):
            cue_lines.append(f'  TRACK {i:02d} AUDIO')
            cue_lines.append(f'    TITLE "{track["title"]}"')
            cue_lines.append(f'    PERFORMER "{self.artist}"')
            cue_lines.append(f'    INDEX 01 {track["minutes"]:02d}:{track["seconds"]:02d}:{track["frames"]:02d}')
        
        return '\n'.join(cue_lines)
    
    def save_cue_file(self, output_path):
        """
        @brief Write the generated CUE content to a file.

        @param output_path Destination file path.
        @return True on success, False on failure.
        """
        content = self.generate_cue_content()
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False


def main():
    """
    @brief Main entry point for the converter.

    Handles user interaction, file parsing, metadata input,
    and saving the final CUE sheet.
    """
    print("="*60)
    print("YOUTUBE TIMESTAMPS TO CUE FILE CONVERTER")
    print("="*60)
    
    generator = CueGenerator()
    
    # Prompt for timestamps file
    while True:
        timestamps_file = input("\nEnter path to timestamps file: ").strip().strip('"\'')
        
        if not timestamps_file:
            print("Error: Please provide a file path")
            continue
        
        try:
            num_tracks = generator.read_timestamps_file(timestamps_file)
            print(f"\n✓ Successfully parsed {num_tracks} tracks from file")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry not in ('y', 'yes'):
                print("Exiting...")
                return
    
    # Confirm parsed tracks
    if not generator.review_tracks():
        print("\nOperation cancelled by user.")
        return
    
    # Gather metadata
    generator.get_user_input()
    
    # Determine output file
    default_output = "output.cue"
    output_file = input(f"\nEnter output filename (default: {default_output}): ").strip() or default_output
    if not output_file.lower().endswith('.cue'):
        output_file += '.cue'
    
    # Save the CUE sheet
    print(f"\nGenerating CUE file: {output_file}")
    if generator.save_cue_file(output_file):
        print(f"✓ CUE file successfully created: {output_file}")
        print("\nCUE FILE PREVIEW:")
        print("="*60)
        print(generator.generate_cue_content())
        print("="*60)
    else:
        print("✗ Failed to create CUE file")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
