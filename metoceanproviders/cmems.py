"""Access to CMEMS[https://marine.copernicus.eu/] datasets, 
you will need to be registered and use your credentials"""

import os
from datetime import datetime
from getpass import getpass

import numpy as np
import xarray as xr

from metoceanproviders import config as cfg

class CredentialsError(Exception):
    """Custom error for incorrect credentials"""

    def __init__(self, username: str, password: str,  message: str):
        self.username = username
        self.password = password
        self.message = message
        super().__init__(message)

class Opendap:
    def __init__(
        self,
        dataset_id: str = None,
        username: str = cfg.CMEMS_USERNAME,
        password: str = cfg.CMEMS_PASSWORD,
    ):
        """Class to access CMEMS-dataset through Opendap service.

        Args:
            dataset_id (str): Id-name of the dataset. Defaults to None.
            username (str, optional): Username to login in CMEMS service. Defaults to None.
            password (str, optional): Password to login in CMEMS service. Defaults to None.

        Notes:
            GLOBAL CURRENTS:  ["cmems_mod_glo_phy_anfc_merged-uv_PT1H-i",
                              "global-analysis-forecast-phy-001-024",
                              "global-analysis-forecast-phy-001-024-3dinst-so",
                              "global-analysis-forecast-phy-001-024-3dinst-thetao",
                              "global-analysis-forecast-phy-001-024-3dinst-uovo",
                              "global-analysis-forecast-phy-001-024-hourly-t-u-v-ssh",
                              "global-analysis-forecast-phy-001-024-monthly"]

            GLOBAL WAVES: ["global-analysis-forecast-wav-001-0272"]

            -----------------------------------------------------------------------------------

            IBI CURRENTS: ["cmems_mod_ibi_phy_anfc_0.027deg-2D_PT15M-m",
                          "cmems_mod_ibi_phy_anfc_0.027deg-2D_PT1H-m",
                          "cmems_mod_ibi_phy_anfc_0.027deg-3D_P1D-m",
                          "cmems_mod_ibi_phy_anfc_0.027deg-3D_P1M-m",
                          "cmems_mod_ibi_phy_anfc_0.027deg-3D_PT1H-m"]

            IBI WAVES: ["dataset-ibi-analysis-forecast-wav-005-005-hourly]

            -----------------------------------------------------------------------------------

            MED CURRENTS: ["med-cmcc-cur-an-fc-d",
                          "med-cmcc-cur-an-fc-h",
                          "med-cmcc-cur-an-fc-hts",
                          "med-cmcc-cur-an-fc-m",
                          "med-cmcc-cur-an-fc-qm",
                          "med-cmcc-mld-an-fc-d",
                          "med-cmcc-mld-an-fc-hts",
                          "med-cmcc-mld-an-fc-m",
                          "med-cmcc-sal-an-fc-d",
                          "med-cmcc-sal-an-fc-h",
                          "med-cmcc-sal-an-fc-hts",
                          "med-cmcc-sal-an-fc-m",
                          "med-cmcc-ssh-an-fc-d",
                          "med-cmcc-ssh-an-fc-hts",
                          "med-cmcc-ssh-an-fc-m",
                          "med-cmcc-ssh-an-fc-qm",
                          "med-cmcc-tem-an-fc-d",
                          "med-cmcc-tem-an-fc-h",
                          "med-cmcc-tem-an-fc-hts",
                          "med-cmcc-tem-an-fc-m"]


        """
        
        self.username = username
        self.password = password
        self.dataset_id = dataset_id.lstrip().rstrip()

        if not self.dataset_id:
            self.dataset_id = input("Enter dataset-id form CMEMS-Opendap service: ")
        if not self.username:
            self.username = getpass("Enter your username: ")
        if not self.password:
            self.password = getpass("Enter your password: ")


        # Connect to datastore
        data_store = self._copernicusmarine_datastore(dataset_id, username, password)
        self.ds = xr.open_dataset(data_store)
        print(
            f"\n\033[1;32m'{username}' is successfully connected to '{dataset_id}'\033[0;0m\n"
        )
        
        # -----------------------------------------------------------------------
        # BUG - Repeted times! waiting response from cmems-service!
        # WORKARROUND - Check there are no repeted times, it there are drop them!
        if len(np.unique(self.ds.time.values)) != len(self.ds.time):
            print(
                "\n\033[1;31mRepeated times founded! --> report to CMEMS - Elena: 'edimedio@mercator-ocean.eu'\033[0;0m\n"
            )
            _, index = np.unique(self.ds["time"], return_index=True)
            self.ds = self.ds.isel(time=index)
        # -----------------------------------------------------------------------

    def crop(
        self,
        variables: list = None,
        times: slice(datetime) = None,
        longitudes: slice(float) = None,
        latitudes: slice(float) = None,
        depths: slice(float) = None,
        method: str = "neareast_outside",
    ):
        """Method to crop dataset in time and spatial coordinates. Also provides variable selection.

        Args:
            variables (list, optional): Variable names to be selected. Defaults to None.
            times (slice, optional): Datetime range to be selected. Defaults to None.
            longitudes (slice, optional): Longitudes range to be selected. Defaults to None.
            latitudes (slice, optional): Latutudes range to be selected. Defaults to None.
            depths (slice, optional): Depths range to be selected. Defaults to None.
            method (str, optional): Method to make the coordinate selection. Defaults to "neareast_outside".
        """

        # Modify coordinates to make the selection based on the method desired
        if method == "neareast_outside":
            # Calculate your domain and add 1 maximum dt, dx, dy as an outside buffer
            if isinstance(times, slice):
                times = slice(
                    times.start
                    - np.diff(self.ds["time"].values)
                    .max()
                    .astype("timedelta64[s]")
                    .item(),
                    times.stop
                    + np.diff(self.ds["time"].values)
                    .max()
                    .astype("timedelta64[s]")
                    .item(),
                )

            if isinstance(longitudes, slice):
                longitudes = slice(
                    longitudes.start - np.diff(self.ds["longitude"].values).max(),
                    longitudes.stop + np.diff(self.ds["longitude"].values).max(),
                )

            if isinstance(latitudes, slice):
                latitudes = slice(
                    latitudes.start - np.diff(self.ds["latitude"].values).max(),
                    latitudes.stop + np.diff(self.ds["latitude"].values).max(),
                )

        # Make the selection of coordinates
        if times is not None:
            if isinstance(times, slice):
                self.ds = self.ds.sel(time=times)
            else:
                self.ds = self.ds.sel(time=times, method="nearest")

        if longitudes is not None:
            if isinstance(longitudes, slice):
                self.ds = self.ds.sel(longitude=longitudes)
            else:
                self.ds = self.ds.sel(longitude=longitudes, method="nearest")

        if latitudes is not None:
            if isinstance(latitudes, slice):
                self.ds = self.ds.sel(latitude=latitudes)
            else:
                self.ds = self.ds.sel(latitude=latitudes, method="nearest")

        if depths is not None:
            if isinstance(depths, slice):
                self.ds = self.ds.sel(detph=depths)
            else:
                self.ds = self.ds.sel(detph=depths, method="nearest")

        # Make the selection of variables
        if variables is not None:
            self.ds = self.ds.get(variables)
        try:
            self.ds.load()
        except:
            print("\n\033[1;33mToo big to be loaded in one request!\033[0;0m\n")

    def to_netcdf(self, output_path: str, netcdf_format: str = None):
        """Save data in netCDF files.
        If the download exceded the maximum size allowed by CMEMS Opendap service,
        the dataset is splited by day and saved in daily netCDF files.

        Args:
            output_path (str): path to the desired file.
            netcdf_format (str, optional): to specify the specific netcdf format, check availables in xarray documentation. Defaults to None.
        """
        output_path = os.path.abspath(output_path)
        try:
            self.ds.to_netcdf(output_path, format=netcdf_format)

        except:
            paths = self.to_daily_netcdf(output_path, netcdf_format)
            output_path = paths

    def to_daily_netcdf(self, output_path, netcdf_format):
        output_dir = os.path.dirname(output_path)
        filename, file_ext = os.path.splitext(os.path.basename(output_path))

        date, datasets = zip(*self.ds.groupby("time.date"))
        paths = [
            f"{output_dir}/{filename}_{d}{file_ext}".replace("-", "") for d in date
        ]
        xr.save_mfdataset(datasets, paths, format=netcdf_format)

        return paths

    def _copernicusmarine_datastore(self, dataset, username, password):
        __author__ = "Copernicus Marine User Support Team"
        __copyright__ = "(C) 2021 E.U. Copernicus Marine Service Information"
        __credits__ = ["E.U. Copernicus Marine Service Information"]
        __license__ = "MIT License - You must cite this source"
        __version__ = "202104"
        __maintainer__ = "D. Bazin, E. DiMedio, C. Giordan"
        __email__ = "servicedesk dot cmems at mercator hyphen ocean dot eu"

        from pydap.cas.get_cookies import setup_session
        from pydap.client import open_url

        cas_url = "https://cmems-cas.cls.fr/cas/login"
        session = setup_session(cas_url, username, password)
        try:
            session.cookies.set("CASTGC", session.cookies.get_dict()["CASTGC"])
        except:
            raise CredentialsError(
                username, password,
                message = f"\n\033[1;31mUsername ({username}) or/and password are incorrect!\033[0;0m\n"
            )
            
        database = ["my", "nrt"]
        url = f"https://{database[0]}.cmems-du.eu/thredds/dodsC/{dataset}"

        try:
            data_store = xr.backends.PydapDataStore(open_url(url, session=session))
        except:
            url = f"https://{database[1]}.cmems-du.eu/thredds/dodsC/{dataset}"
            data_store = xr.backends.PydapDataStore(open_url(url, session=session))
        return data_store


if __name__ == "__main__":

    data = Opendap()
    print(data.ds)
