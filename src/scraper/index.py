import os
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib import parse, request

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr
from botocore.client import ClientError
from bs4 import BeautifulSoup, Tag

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table
else:
    Table = object

logger = Logger()


@dataclass
class RoomInfo:
    id: str
    image_urls: typing.List[str]
    floor: str
    price_rent: str
    price_maintenance: str
    price_deposit: str
    price_gratuity: str
    section_type: str
    area: str


@dataclass
class BuildingInfo:
    name: str
    image_url: str
    address: str
    accesses: typing.List[str]
    age: str
    floor: str
    room_infos: typing.List[RoomInfo]


class SuumoScraper:
    def __init__(self, entry_url: str) -> None:
        self.parsed_url = parse.urlparse(entry_url)
        self.params = [
            (k, v)
            for k, v in parse.parse_qsl(self.parsed_url.query)
            if k != "page"
        ]

    def scrape(self) -> typing.List[BuildingInfo]:
        logger.info("scraping...")

        page = 1
        building_infos: typing.List[BuildingInfo] = []
        while infos := self._scrape_page(page):
            building_infos.extend(infos)
            page += 1

        logger.info(f"{len(building_infos)} buildings were found.")

        return building_infos

    def _scrape_page(self, page: int) -> typing.List[BuildingInfo]:
        query = "&".join(
            [f"{k}={v}" for k, v in self.params] + [f"page={page}"]
        )
        url = parse.urlunparse(self.parsed_url._replace(query=query))

        logger.debug(url)

        soup = BeautifulSoup(request.urlopen(url), "html.parser")

        building_infos = [
            self._scrape_building(building_tag)
            for building_tag in soup.find_all("div", class_="cassetteitem")
        ]

        return building_infos

    def _scrape_building(self, building_tag: Tag) -> BuildingInfo:
        room_infos = [
            self._scrape_room(room_tag)
            for room_tag in building_tag.find(
                "div", class_="cassetteitem-item"
            ).find_all("tbody")
        ]

        building_info = BuildingInfo(
            name=building_tag.find(
                "div",
                class_="cassetteitem_content-title",
            ).text,
            image_url=building_tag.find(
                "div", class_="cassetteitem_object-item"
            ).find("img")["rel"],
            address=building_tag.find(
                "li", class_="cassetteitem_detail-col1"
            ).text,
            accesses=[
                tag.text.strip()
                for tag in building_tag.find_all(
                    "div", class_="cassetteitem_detail-text"
                )
            ],
            age=(
                building_tag.find("li", class_="cassetteitem_detail-col3")
                .find_all("div")[0]
                .text.strip()
            ),
            floor=(
                building_tag.find("li", class_="cassetteitem_detail-col3")
                .find_all("div")[1]
                .text.strip()
            ),
            room_infos=room_infos,
        )

        logger.debug(building_info)

        return building_info

    def _scrape_room(self, room_tag: Tag) -> RoomInfo:
        room_info = RoomInfo(
            id=room_tag.find("input").get("value"),
            image_urls=room_tag.find(
                "div", class_="casssetteitem_other-thumbnail"
            )
            .get("data-imgs")
            .split(","),
            floor=room_tag.find_all("td")[2].text.strip(),
            price_rent=room_tag.find(
                "span", class_="cassetteitem_price--rent"
            ).text.strip(),
            price_maintenance=room_tag.find(
                "span", class_="cassetteitem_price--administration"
            ).text.strip(),
            price_deposit=room_tag.find(
                "span", class_="cassetteitem_price--deposit"
            ).text.strip(),
            price_gratuity=room_tag.find(
                "span", class_="cassetteitem_price--gratuity"
            ).text.strip(),
            section_type=room_tag.find(
                "span", class_="cassetteitem_madori"
            ).text.strip(),
            area=room_tag.find("span", class_="cassetteitem_menseki").text,
        )

        logger.debug(room_info)

        return room_info


class RoomInfoRegister:
    def __init__(
        self,
        building_infos: typing.List[BuildingInfo],
        table_name: str,
    ) -> None:
        self.building_infos = building_infos
        self.table = self._get_table(table_name)

    def _get_table(self, table_name: str) -> Table:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        return table

    def register(self) -> None:
        logger.info("register...")

        for building_info in self.building_infos:
            for room_info in building_info.room_infos:
                self._register_room_info(
                    room_info=room_info,
                    building_info=building_info,
                )

    def _register_room_info(
        self,
        room_info: RoomInfo,
        building_info: BuildingInfo,
    ) -> None:
        building_info_dict = building_info.__dict__
        del building_info_dict["room_infos"]

        try:
            self.table.put_item(
                Item={
                    "id": room_info.id,
                    "room_info": room_info.__dict__,
                    "building_info": building_info_dict,
                },
                ConditionExpression=Attr("id").not_exists(),
            )
        except ClientError as e:
            if (
                e.response["Error"]["Code"]
                == "ConditionalCheckFailedException"  # noqa
            ):
                pass
            else:
                raise (e)


def main(entry_url: str, table_name: str) -> None:
    scraper = SuumoScraper(entry_url=entry_url)

    building_infos = scraper.scrape()
    register = RoomInfoRegister(
        building_infos=building_infos,
        table_name=table_name,
    )

    register.register()


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> None:
    main(
        entry_url=os.environ["ENTRY_URL"],
        table_name=os.environ["TABLE_NAME"],
    )
