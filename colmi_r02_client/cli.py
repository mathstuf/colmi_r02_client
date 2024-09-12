"""
A python client for connecting to the Colmi R02 Smart ring
"""

from datetime import datetime, timezone
from pathlib import Path
import logging
import time

import asyncclick as click
from bleak import BleakScanner

from colmi_r02_client.client import Client
from colmi_r02_client.hr import HeartRateLog

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")

logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.option(
    "--record/--no-record",
    default=False,
    help="Write all received packets to a file",
)
@click.option("--address", required=True, help="Bluetooth address")
@click.pass_context
async def cli_client(context: click.Context, debug: bool, record: bool, address: str) -> None:
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("bleak").setLevel(logging.INFO)

    record_to = None
    if record:
        now = int(time.time())
        captures = Path("captures")
        captures.mkdir(exist_ok=True)
        record_to = captures / Path(f"colmi_response_capture_{now}.bin")
        logger.info(f"Recording responses to {record_to}")

    client = Client(address, record_to=record_to)

    context.obj = await context.with_async_resource(client)


@cli_client.command()
@click.pass_obj
async def info(client: Client) -> None:
    """Get device info and battery level"""

    print("device info", await client.get_device_info())
    print("battery:", await client.get_battery())


@cli_client.command()
@click.option(
    "--target",
    type=click.DateTime(),
    required=True,
    help="The date you want logs for",
)
@click.pass_obj
async def get_heart_rate_log(client: Client, target: datetime) -> None:
    """Get heart rate for given date"""

    log = await client.get_heart_rate_log(target)
    print("Data:", log)
    if isinstance(log, HeartRateLog):
        for hr, ts in log.heart_rates_with_times():
            if hr != 0:
                print(f"{ts.strftime('%H:%M')}, {hr}")


@cli_client.command()
@click.option(
    "--when",
    type=click.DateTime(),
    required=False,
    help="The date and time you want to set the ring to",
)
@click.pass_obj
async def set_time(client: Client, when: datetime | None) -> None:
    """
    Set the time on the ring, required if you want to be able to interpret any of the logged data
    """

    if when is None:
        when = datetime.now(tz=timezone.utc)
    await client.set_time(when)


@cli_client.command()
@click.pass_obj
async def get_heart_rate_log_settings(client: Client) -> None:
    """Get heart rate log settings"""

    click.echo("heart rate log settings:")
    click.echo(await client.get_heart_rate_log_settings())

@cli_client.command()
@click.pass_obj
async def get_real_time_heart_rate(client: Client) -> None:
    """Get real time heart rate.

    TODO: add number of readings
    """

    click.echo("Starting reading, please wait.")
    click.echo(await client.get_realtime_heart_rate())

DEVICE_NAME_PREFIXES = [
    "R01",
    "R02",
    "R03",
    "R04",
    "R05",
    "R06",
    "R07",
    "VK-5098",
    "MERLIN",
    "Hello Ring",
    "RING1",
    "boAtring",
    "TR-R02",
    "SE",
    "EVOLVEO",
    "GL-SR2",
    "Blaupunkt",
    "KSIX RING",
]


@click.group()
async def util():
    """Generic utilities for the R02 that don't need an address."""


@util.command()
async def scan():
    """Scan for possible devices based on known prefixes and print the bluetooth address."""

    # TODO maybe bluetooth specific stuff like this should be in another package?
    devices = await BleakScanner.discover()

    if len(devices) > 0:
        print("Found device(s)")
        print(f"{'Name':>20}  | Address")
        print("-" * 44)
        for d in devices:
            name = d.name
            if name and any(name for p in DEVICE_NAME_PREFIXES if name.startswith(p)):
                print(f"{name:>20}  |  {d.address}")
    else:
        print("No devices found. Try moving the ring closer to computer")