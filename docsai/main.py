from pathlib import Path
from typing import List, Optional, Union
from typing_extensions import Annotated

import google.generativeai as genai
import toml
import typer
from rich import print

app = typer.Typer(no_args_is_help=True)


@app.command()
def document(
    files: Annotated[List[Path], typer.Argument(help="File or files to document")],
    replace: Annotated[
        bool, typer.Option(help="Replace file with the new code with documentation")
    ] = False,
    language: Annotated[
        Optional[str], typer.Option(help="Language for the documentation")
    ] = "english",
) -> None:
    """
    Document code files using a generative AI model.

    Args:
        files (List[Path]): List of file paths to document.
        replace (bool, optional): Whether to replace the original files with the documented versions. Defaults to False.
        language (Optional[str], optional): Language for the documentation. Defaults to 'english'.
    """
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=f"You are a good programmer. Expert at documenting code. You will be passed code that may or may not have documentation. Your job will be to write the documentation for this code inside the code. If the code is in python you are going to put strong typing in it, otherwise you are not going to change the code. Your ourput will be only the code. The documentation will be in {language}",
    )
    init_config()
    handling_files(files=files, replace=replace, model=model)


@app.command()
def config(
    api_key: Annotated[str, typer.Option(help="Api key for gemini")],
    config_path: Annotated[Path, typer.Option(help="Configuration path")] = Path.home()
    / "docsai.toml",
) -> None:

    """
    Configures the API key for the Gemini service and stores the configuration in a TOML file.

    Args:
        api_key (str): The API key required to authenticate and interact with the Gemini service.
        config_path (Path, optional): The path to the configuration file. Defaults to 'docsai.toml' in the user's home directory.
    
    Raises:
        typer.Exit: If the configuration file does not exist, the function prints an error message and exits the program.
    
    Functionality:
    - Opens the TOML configuration file at the specified path (`config_path`). 
    - If the file does not exist, it prompts the user to create the file and exits the program.
    - If the file exists but does not contain the necessary sections ('API' or 'PATH'), these sections are created.
    - The API key is stored in the 'API' section, and the path to the configuration file is stored in the 'PATH' section.
    - The updated configuration is then saved back to the TOML file.
    """

    try:
        with open(config_path, "r") as file:
            config_file = toml.load(file)
    except FileNotFoundError:
        typer.echo(f"Configuration file not found at {config_path}, please create one.")
        raise typer.Exit(code=1)

    if "API" not in config_file:
        config_file["API"] = {}

    if "PATH" not in config_file:
        config_file["PATH"] = {}

    config_file["API"]["API_KEY"] = api_key
    config_file["PATH"]["PATH"] = config_path

    with open(config_path, "w") as file:
        toml.dump(config_file, file)


def init_config() -> None:
    """
    Initializes the configuration file and sets up the API key.

    If the configuration file doesn't exist, it will be created.
    If the API key is not found, the user will be prompted to configure it.
    """

    config_path: Path = Path.home() / "docsai.toml"

    if not config_path.exists():
        config_path.write_text("")

    api_key = load_config(config_path)

    if api_key is False:
        typer.echo(
            "API key not found. Please configure it using 'docsai config --api-key'."
        )
        raise typer.Exit(code=1)

    genai.configure(api_key=api_key)


def load_config(config_path: Path) -> Union[str, bool]:
    """
    Loads the configuration file and returns the API key.

    Args:
        config_path (Path): The path to the configuration file.

    Returns:
        Union[str, bool]: The API key if found, otherwise False.
    """

    try:
        with open(config_path, "r") as file:
            config_file = toml.load(file)
            api_key = config_file["API"]["API_KEY"]
        return api_key

    except KeyError:
        return False


def handling_files(
    files: List[Path],
    replace: bool,
    model: genai.GenerativeModel,
    output_file: Optional[Path] = None,
) -> None:
    """
    Handles the documentation of individual files.

    Args:
        files (List[Path]): List of file paths to document.
        replace (bool): Whether to replace the original files with the documented versions.
        model (genai.GenerativeModel): The generative AI model to use for documentation.
        output_file (Optional[Path]): The path to the output file. If not provided, the output file will be named `doc_{file}`.
    """

    for file in files:

        if replace:
            output_file: Path = Path(file).resolve()

        else:
            output_file: Path = Path(file).resolve().with_name(f"doc_{file.name}")

        try:
            with open(file.resolve(), "r") as code_file:
                file_content = code_file.read()
                doc_code = model.generate_content(file_content).text
                doc_code = doc_code.splitlines()[1:-1]
                doc_code = "\n".join(doc_code)

            with open(output_file, "w") as out_file:
                out_file.write(doc_code)
                typer.echo(f"Documentation for {file.name} ready")

        except FileNotFoundError:
            print(f"The file {file} doesn't exist")
            raise typer.Exit(code=1)


if __name__ == "__main__":

    app()
