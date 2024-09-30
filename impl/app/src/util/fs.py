import csv
import json
import logging
import os

from typing import Iterator

# This class is used to interact with the local filesystem, such as
# reading and writing text, csv, and json files.
# Chris Joakim, Microsoft


class FS:
    @classmethod
    def as_unix_filename(cls, filename: str) -> str:
        """Return the given filename with unix slashes."""
        if filename.upper().startswith("C:"):
            return filename[2:].replace("\\", "/")
        return filename

    @classmethod
    def read(cls, infile: str) -> str | None:
        """Read the given file, return the file contents str or None."""
        if os.path.isfile(infile):
            with open(file=infile, encoding="utf-8", mode="rt") as file:
                return file.read()
        return None

    @classmethod
    def readr(cls, infile: str) -> str | None:
        """Read the given file with mode 'r', return the file contents str or None."""
        if os.path.isfile(infile):
            with open(file=infile, encoding="utf-8", mode="r") as file:
                return file.read()
        return None

    @classmethod
    def read_binary(cls, infile: str) -> str | None:
        """Read the given binary file with mode 'rb', return the bytes or None."""
        if os.path.isfile(infile):
            with open(file=infile, mode="rb") as file:
                return file.read()
        return None

    @classmethod
    def read_lines(cls, infile: str) -> list[str] | None:
        """Read the given file, return an array of lines(strings) or None"""
        if os.path.isfile(infile):
            lines = []
            with open(file=infile, encoding="utf-8", mode="rt") as file:
                for line in file:
                    lines.append(line)
            return lines
        return None

    @classmethod
    def read_single_line(cls, infile: str) -> str | None:
        """Read the given file, return the first line or None"""
        lines = cls.read_lines(infile)
        if lines is not None:
            if len(lines) > 0:
                return lines[0].strip()
        return None

    @classmethod
    def read_encoded_lines(cls, infile: str, encoding="cp1252") -> list[str] | None:
        """
        Read the given file, with the given encoding.
        Return an array of lines(strings) or None.
        """
        if os.path.isfile(infile):
            lines = []
            with open(file=infile, encoding=encoding, mode="rt") as file:
                for line in file:
                    lines.append(line)
            return lines
        return None

    @classmethod
    def read_win_cp1252(cls, infile: str) -> str | None:
        """
        Read the given file with Windows encoding cp1252.
        Return an array of lines(strings) or None.
        """
        if os.path.isfile(infile):
            with open(file=os.path.join(infile), encoding="cp1252", mode="r") as file:
                return file.read()
        return None

    @classmethod
    def read_csv_as_dicts(
        cls, infile: str, delim=",", dialect="excel"
    ) -> list[str] | None:
        """
        Read the given csv filename, return an array of dicts or None.
        """
        if os.path.isfile(infile):
            rows = []
            with open(file=infile, encoding="utf-8", mode="rt") as csvfile:
                rdr = csv.DictReader(csvfile, dialect=dialect, delimiter=delim)
                for row in rdr:
                    rows.append(row)
            return rows
        return None

    @classmethod
    def read_csv_as_rows(cls, infile: str, delim=",", skip=0) -> list[str] | None:
        """
        Read the given csv filename, return an array of csv rows or None.
        """
        if os.path.isfile(infile):
            rows = []
            with open(file=infile, encoding="utf-8", mode="rt") as csvfile:
                rdr = csv.reader(csvfile, delimiter=delim)
                for idx, row in enumerate(rdr):
                    if idx >= skip:
                        rows.append(row)
            return rows
        return None

    @classmethod
    def read_json(cls, infile: str, encoding="utf-8") -> dict | list | None:
        """Read the given JSON file, return either a list, a dict, or None."""
        if os.path.isfile(infile):
            with open(file=infile, encoding=encoding, mode="rt") as file:
                return json.loads(file.read())
        return None

    @classmethod
    def write_json(cls, obj: object, outfile: str, pretty=True, verbose=True) -> None:
        """Write the given object to the given file as JSON."""
        if obj is not None:
            jstr = None
            if pretty is True:
                jstr = json.dumps(obj, sort_keys=False, indent=2)
            else:
                jstr = json.dumps(obj)

            with open(file=outfile, encoding="utf-8", mode="w") as file:
                file.write(jstr)
                if verbose is True:
                    logging.warning(f"file written: {outfile}")

    @classmethod
    def write_lines(cls, lines: list[str], outfile: str, verbose=True) -> None:
        """Write the given str lines to the given file."""
        if lines is not None:
            with open(file=outfile, encoding="utf-8", mode="w") as file:
                for line in lines:
                    file.write(line + "\n")  # os.linesep)  # \n works on Windows
                if verbose is True:
                    logging.warning(f"file written: {outfile}")

    @classmethod
    def text_file_iterator(cls, infile: str) -> Iterator[str] | None:
        """Return a line generator that can be iterated with iterate()"""
        if os.path.isfile(infile):
            with open(file=infile, encoding="utf-8", mode="rt") as file:
                for line in file:
                    yield line.strip()

    @classmethod
    def write(cls, outfile: str, string_value: str, verbose=True) -> None:
        """Write the given string to the given file."""
        if outfile is not None:
            if string_value is not None:
                with open(file=outfile, encoding="utf-8", mode="w") as file:
                    file.write(string_value)
                    if verbose is True:
                        logging.warning(f"file written: {outfile}")

    @classmethod
    def list_directories_in_dir(cls, basedir: str) -> list[str] | None:
        """Return a list of directories in the given directory, or None."""
        if os.path.isdir(basedir):
            files = []
            for file in os.listdir(basedir):
                dir_or_file = os.path.join(basedir, file)
                if os.path.isdir(dir_or_file):
                    files.append(file)
            return files
        return None

    @classmethod
    def list_files_in_dir(cls, basedir: str) -> list[str] | None:
        """Return a list of files in the given directory, or None."""
        if os.path.isdir(basedir):
            files = []
            for file in os.listdir(basedir):
                dir_or_file = os.path.join(basedir, file)
                if os.path.isdir(dir_or_file):
                    pass
                else:
                    files.append(file)
            return files
        return None

    @classmethod
    def walk(cls, directory: str) -> list[dict] | None:
        """Return a list of dicts for each file in the given directory, or None."""
        if os.path.isdir(directory):
            files = []
            for dir_name, _, base_names in os.walk(directory):
                for base_name in base_names:
                    full_name = f"{dir_name}/{base_name}"
                    entry = {}
                    entry["base"] = base_name
                    entry["dir"] = dir_name
                    entry["full"] = full_name
                    entry["abspath"] = os.path.abspath(full_name)
                    files.append(entry)
            return files
        return None

    @classmethod
    def read_csvfile_into_rows(cls, infile: str, delim=",") -> list | None:
        """Read the given csv filename, return an array of csv rows or None."""
        if os.path.isfile(infile):
            rows = []  # return a list of csv rows
            with open(file=infile, encoding="utf-8", mode="rt") as csvfile:
                reader = csv.reader(csvfile, delimiter=delim)
                for row in reader:
                    rows.append(row)
            return rows
        return None

    @classmethod
    def read_csvfile_into_objects(cls, infile: str, delim=",") -> list[object] | None:
        """Read the given csv filename, return an array of objects or None."""
        if os.path.isfile(infile):
            objects = []
            with open(file=infile, encoding="utf-8", mode="rt") as csvfile:
                reader = csv.reader(csvfile, delimiter=delim)
                headers = None
                for idx, row in enumerate(reader):
                    if idx == 0:
                        headers = row
                    else:
                        if len(row) == len(headers):
                            obj = {}
                            for field_idx, field_name in enumerate(headers):
                                key = field_name.strip().lower()
                                obj[key] = row[field_idx].strip()
                            objects.append(obj)
            return objects
        return None
