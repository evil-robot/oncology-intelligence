"""
Social Determinants of Health (SDOH) data loader.

Loads CDC Social Vulnerability Index (SVI) data and other SDOH metrics
for geographic overlay on search trends.
"""

import logging
from typing import Optional
from dataclasses import dataclass

import pandas as pd
import httpx

logger = logging.getLogger(__name__)

# CDC SVI data URL (2020 data at county level)
CDC_SVI_URL = "https://svi.cdc.gov/data/SVI_2020_US_county.csv"

# State FIPS code mapping
STATE_FIPS = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District of Columbia", "12": "Florida", "13": "Georgia", "15": "Hawaii",
    "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa",
    "20": "Kansas", "21": "Kentucky", "22": "Louisiana", "23": "Maine",
    "24": "Maryland", "25": "Massachusetts", "26": "Michigan", "27": "Minnesota",
    "28": "Mississippi", "29": "Missouri", "30": "Montana", "31": "Nebraska",
    "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
    "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio",
    "40": "Oklahoma", "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island",
    "45": "South Carolina", "46": "South Dakota", "47": "Tennessee", "48": "Texas",
    "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
    "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming",
}

# State abbreviation to FIPS
STATE_ABBREV_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56",
}


@dataclass
class SDOHRegion:
    """SDOH data for a geographic region."""

    geo_code: str
    name: str
    level: str  # "state" or "county"

    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Population
    population: Optional[int] = None

    # SVI components (0-1, higher = more vulnerable)
    svi_overall: Optional[float] = None
    svi_socioeconomic: Optional[float] = None
    svi_household_disability: Optional[float] = None
    svi_minority_language: Optional[float] = None
    svi_housing_transport: Optional[float] = None

    # Additional metrics
    median_income: Optional[int] = None
    uninsured_rate: Optional[float] = None


class SDOHLoader:
    """Load and process SDOH data from CDC and other sources."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir
        self._county_data: Optional[pd.DataFrame] = None
        self._state_data: Optional[pd.DataFrame] = None

    async def load_county_svi(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Load CDC SVI data at county level.

        Returns DataFrame with columns:
        - fips: County FIPS code
        - state_fips: State FIPS code
        - county: County name
        - state: State name
        - population: Total population
        - svi_*: SVI theme scores
        """
        if self._county_data is not None and not force_refresh:
            return self._county_data

        logger.info("Loading CDC SVI county data...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(CDC_SVI_URL)
                response.raise_for_status()

            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))

            # Select and rename relevant columns
            columns_map = {
                "FIPS": "fips",
                "STATE": "state",
                "ST_ABBR": "state_abbr",
                "COUNTY": "county",
                "E_TOTPOP": "population",
                "RPL_THEMES": "svi_overall",
                "RPL_THEME1": "svi_socioeconomic",
                "RPL_THEME2": "svi_household_disability",
                "RPL_THEME3": "svi_minority_language",
                "RPL_THEME4": "svi_housing_transport",
                "EP_UNINSUR": "uninsured_rate",
                "EP_POV150": "poverty_rate",
            }

            # Filter to columns that exist
            existing_cols = {k: v for k, v in columns_map.items() if k in df.columns}
            df = df[list(existing_cols.keys())].rename(columns=existing_cols)

            # Clean data
            df["fips"] = df["fips"].astype(str).str.zfill(5)
            df["state_fips"] = df["fips"].str[:2]

            # Handle missing values
            for col in ["svi_overall", "svi_socioeconomic", "svi_household_disability",
                       "svi_minority_language", "svi_housing_transport"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    df[col] = df[col].clip(0, 1)  # SVI should be 0-1

            self._county_data = df
            logger.info(f"Loaded SVI data for {len(df)} counties")
            return df

        except Exception as e:
            logger.error(f"Error loading SVI data: {e}")
            return pd.DataFrame()

    def aggregate_to_state(self, county_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate county-level SVI to state level using population weighting.

        Args:
            county_df: County-level SVI DataFrame

        Returns:
            State-level SVI DataFrame
        """
        if county_df.empty:
            return pd.DataFrame()

        # Group by state
        numeric_cols = ["svi_overall", "svi_socioeconomic", "svi_household_disability",
                       "svi_minority_language", "svi_housing_transport", "uninsured_rate"]

        existing_numeric = [c for c in numeric_cols if c in county_df.columns]

        # Population-weighted average for SVI scores
        def weighted_avg(group, col):
            weights = group["population"].fillna(0)
            values = group[col].fillna(0)
            if weights.sum() == 0:
                return values.mean()
            return (values * weights).sum() / weights.sum()

        state_agg = county_df.groupby("state_fips").agg({
            "state": "first",
            "state_abbr": "first" if "state_abbr" in county_df.columns else lambda x: "",
            "population": "sum",
            **{col: lambda g, c=col: weighted_avg(g, c) for col in existing_numeric}
        }).reset_index()

        state_agg["geo_code"] = "US-" + state_agg["state_abbr"]

        self._state_data = state_agg
        return state_agg

    def get_state_sdoh(self, state_code: str) -> Optional[SDOHRegion]:
        """
        Get SDOH data for a state.

        Args:
            state_code: State code (e.g., "US-CA" or "CA")

        Returns:
            SDOHRegion or None if not found
        """
        if self._state_data is None:
            logger.warning("State SDOH data not loaded")
            return None

        # Normalize state code
        if state_code.startswith("US-"):
            state_abbr = state_code[3:]
        else:
            state_abbr = state_code

        row = self._state_data[self._state_data["state_abbr"] == state_abbr]
        if row.empty:
            return None

        row = row.iloc[0]
        return SDOHRegion(
            geo_code=f"US-{state_abbr}",
            name=row.get("state", state_abbr),
            level="state",
            population=int(row["population"]) if pd.notna(row.get("population")) else None,
            svi_overall=float(row["svi_overall"]) if pd.notna(row.get("svi_overall")) else None,
            svi_socioeconomic=float(row["svi_socioeconomic"]) if pd.notna(row.get("svi_socioeconomic")) else None,
            svi_household_disability=float(row["svi_household_disability"]) if pd.notna(row.get("svi_household_disability")) else None,
            svi_minority_language=float(row["svi_minority_language"]) if pd.notna(row.get("svi_minority_language")) else None,
            svi_housing_transport=float(row["svi_housing_transport"]) if pd.notna(row.get("svi_housing_transport")) else None,
            uninsured_rate=float(row["uninsured_rate"]) if pd.notna(row.get("uninsured_rate")) else None,
        )


# State centroids for mapping (approximate)
STATE_CENTROIDS = {
    "AL": (32.806671, -86.791130), "AK": (61.370716, -152.404419),
    "AZ": (33.729759, -111.431221), "AR": (34.969704, -92.373123),
    "CA": (36.116203, -119.681564), "CO": (39.059811, -105.311104),
    "CT": (41.597782, -72.755371), "DE": (39.318523, -75.507141),
    "FL": (27.766279, -81.686783), "GA": (33.040619, -83.643074),
    "HI": (21.094318, -157.498337), "ID": (44.240459, -114.478828),
    "IL": (40.349457, -88.986137), "IN": (39.849426, -86.258278),
    "IA": (42.011539, -93.210526), "KS": (38.526600, -96.726486),
    "KY": (37.668140, -84.670067), "LA": (31.169546, -91.867805),
    "ME": (44.693947, -69.381927), "MD": (39.063946, -76.802101),
    "MA": (42.230171, -71.530106), "MI": (43.326618, -84.536095),
    "MN": (45.694454, -93.900192), "MS": (32.741646, -89.678696),
    "MO": (38.456085, -92.288368), "MT": (46.921925, -110.454353),
    "NE": (41.125370, -98.268082), "NV": (38.313515, -117.055374),
    "NH": (43.452492, -71.563896), "NJ": (40.298904, -74.521011),
    "NM": (34.840515, -106.248482), "NY": (42.165726, -74.948051),
    "NC": (35.630066, -79.806419), "ND": (47.528912, -99.784012),
    "OH": (40.388783, -82.764915), "OK": (35.565342, -96.928917),
    "OR": (44.572021, -122.070938), "PA": (40.590752, -77.209755),
    "RI": (41.680893, -71.511780), "SC": (33.856892, -80.945007),
    "SD": (44.299782, -99.438828), "TN": (35.747845, -86.692345),
    "TX": (31.054487, -97.563461), "UT": (40.150032, -111.862434),
    "VT": (44.045876, -72.710686), "VA": (37.769337, -78.169968),
    "WA": (47.400902, -121.490494), "WV": (38.491226, -80.954453),
    "WI": (44.268543, -89.616508), "WY": (42.755966, -107.302490),
}
