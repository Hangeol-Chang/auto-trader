
import json
import os
import pandas as pd
from typing import List, Dict, Union

def load_column_map() -> Dict:
    """
    Load column mapping from column_map.json
    
    Returns:
        Dict: Column mapping dictionary
    """
    # Get the directory of the current file and navigate to params
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    column_map_path = os.path.join(project_root, "params", "column_map.json")
    
    try:
        with open(column_map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Column mapping file not found at: {column_map_path}")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in column mapping file")

def columnname_convert(cols: Union[List[str], str], as_is: str = "kis", to_be: str = "my_app") -> Union[List[str], str]:
    """
    Convert column names from one format to another using the column mapping.
    
    Args:
        cols: Column name(s) to convert (string or list of strings)
        as_is: Source format ("kis", "my_app", "kor")
        to_be: Target format ("kis", "my_app", "kor")
    
    Returns:
        Converted column name(s) in the same format as input (string or list)
    """
    # Load column mapping
    column_map = load_column_map()
    
    # Validate formats
    if as_is not in column_map or to_be not in column_map:
        available_formats = list(column_map.keys())
        raise ValueError(f"Invalid format. Available formats: {available_formats}")
    
    # Get mapping tables
    source_table = column_map[as_is]["table"]
    target_table = column_map[to_be]["table"]
    
    # Create reverse mapping for source format (value -> key)
    source_reverse_map = {v: k for k, v in source_table.items()}
    
    def convert_single_column(col_name: str) -> str:
        # Find the standardized key for this column value
        if col_name in source_reverse_map:
            standard_key = source_reverse_map[col_name]
            # Return the target format value for this standard key
            if standard_key in target_table:
                return target_table[standard_key]
        
        # If no mapping found, return original name
        return col_name
    
    # Handle single string input
    if isinstance(cols, str):
        return convert_single_column(cols)
    
    # Handle list input
    if isinstance(cols, list):
        return [convert_single_column(col) for col in cols]
    
    # Invalid input type
    raise TypeError("cols must be either a string or a list of strings")

def convert_dataframe_columns(df, as_is: str = "kis", to_be: str = "my_app"):
    """
    Convert DataFrame column names from one format to another.
    
    Args:
        df: pandas DataFrame with columns to convert
        as_is: Source format ("kis", "my_app", "kor")  
        to_be: Target format ("kis", "my_app", "kor")
        
    Returns:
        pandas DataFrame with converted column names
    """
    # Get current column names
    current_columns = list(df.columns)
    
    # Convert column names
    new_columns = columnname_convert(current_columns, as_is=as_is, to_be=to_be)
    
    # Create a copy of the DataFrame with new column names
    df_converted = df.copy()
    df_converted.columns = new_columns
    
    return df_converted

def convert_dataframe_columns_dual_header(df, as_is: str = "kis", to_be: str = "my_app"):
    """
    Convert DataFrame column names to dual header format with Korean descriptions.
    
    Args:
        df: pandas DataFrame with columns to convert
        as_is: Source format ("kis", "my_app", "kor")  
        to_be: Target format ("kis", "my_app", "kor")
        
    Returns:
        pandas DataFrame with MultiIndex columns (Korean description, target format)
    """
    # Get current column names
    current_columns = list(df.columns)
    
    # Convert column names to target format
    target_columns = columnname_convert(current_columns, as_is=as_is, to_be=to_be)
    
    # Convert column names to Korean format
    korean_columns = columnname_convert(current_columns, as_is=as_is, to_be="kor")
    
    # Create dual header tuples (Korean description, target format)
    dual_columns = [(kor, target) for kor, target in zip(target_columns, korean_columns)]
    
    # Create a copy of the DataFrame with MultiIndex columns
    df_converted = df.copy()
    df_converted.columns = pd.MultiIndex.from_tuples(dual_columns, names=[to_be, 'KOR'])
    
    return df_converted

def get_available_columns(format_name: str = "my_app") -> List[str]:
    """
    Get list of available columns for a specific format.
    
    Args:
        format_name: Format name ("kis", "my_app", "kor")
        
    Returns:
        List of available column names for the format
    """
    column_map = load_column_map()
    
    if format_name not in column_map:
        available_formats = list(column_map.keys())
        raise ValueError(f"Invalid format. Available formats: {available_formats}")
    
    return list(column_map[format_name]["table"].keys())