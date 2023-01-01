import os
import typing

import boto3
import pytest
from bs4 import BeautifulSoup, Tag
from moto import mock_dynamodb
from pytest_mock import MockerFixture

from src.scraper.index import (
    BuildingInfo,
    RoomInfo,
    RoomInfoRegister,
    SuumoScraper,
)


class TestSuumoScraper:
    @pytest.fixture
    def target(self) -> SuumoScraper:
        return SuumoScraper("https://example.com/test?foo=bar&page=5")

    def _get_tag(self, html: str) -> Tag:
        soup = BeautifulSoup(html, "html.parser")
        return soup.currentTag()[0]

    def test_init(self, target: SuumoScraper) -> None:
        assert target.params == [("foo", "bar")]

    def test_scrape(self, target: SuumoScraper, mocker: MockerFixture) -> None:
        mocked_scrape_page = mocker.patch.object(target, "_scrape_page")
        mocked_scrape_page.side_effect = [
            [
                BuildingInfo(
                    name="ビル",
                    image_url="https://image.example.com",
                    address="住所",
                    accesses=["駅から徒歩1分"],
                    age="新築",
                    floor="10階",
                    room_infos=[],
                )
            ],
            [],
        ]

        result = target.scrape()

        assert len(result) == 1
        mocked_scrape_page.assert_has_calls([mocker.call(1), mocker.call(2)])

    def test_scrape_page(
        self,
        target: SuumoScraper,
        mocker: MockerFixture,
    ) -> None:
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <title>Document</title>
        </head>
        <body>
        <div class="cassetteitem">1</div>
        <div class="cassetteitem">2</div>
        </body>
        </html>
        """
        mocked_urlopen = mocker.Mock(return_value=html)
        mocked_request = mocker.patch("src.scraper.index.request")
        mocked_request.urlopen = mocked_urlopen
        mocked_scrape_building = mocker.patch.object(
            target,
            "_scrape_building",
        )
        mocked_scrape_building.side_effect = [
            BuildingInfo(
                name="ビル1",
                image_url="https://image.example.com",
                address="住所",
                accesses=["駅から徒歩1分"],
                age="新築",
                floor="10階",
                room_infos=[],
            ),
            BuildingInfo(
                name="ビル2",
                image_url="https://image.example.com",
                address="住所",
                accesses=["駅から徒歩1分"],
                age="新築",
                floor="10階",
                room_infos=[],
            ),
        ]

        infos = target._scrape_page(1)

        assert len(infos) == 2
        assert infos[0].name == "ビル1"
        assert infos[1].name == "ビル2"
        mocked_urlopen.assert_called_once_with(
            "https://example.com/test?foo=bar&page=1"
        )
        mocked_scrape_building.assert_has_calls(
            [
                mocker.call(
                    self._get_tag('<div class="cassetteitem">1</div>'),
                ),
                mocker.call(
                    self._get_tag('<div class="cassetteitem">2</div>'),
                ),
            ]
        )

    def test_scrape_building(self, target: SuumoScraper) -> None:
        html = """
        <div class="cassetteitem">
        <div class="cassetteitem-detail">
        <div class="cassetteitem-detail-object">
        <div class="cassetteitem_object">
        <div class="cassetteitem_object-item">
        <img rel="https://example.com/image.jpg" />
        </div>
        </div>
        </div>
        <div class="cassetteitem-detail-body">
        <div class="cassetteitem_content">
        <div class="cassetteitem_content-label">
        <span class="ui-pct ui-pct--util1">賃貸マンション</span>
        </div>
        <div class="cassetteitem_content-title">ビルディング</div>
        <div class="cassetteitem_content-body">
        <ul class="cassetteitem_detail">
        <li class="cassetteitem_detail-col1">東京都どこか</li>
        <li class="cassetteitem_detail-col2">
        <div class="cassetteitem_detail-text">
        ＪＲ中央線/東京駅 歩1分
        </div>
        </li>
        <li class="cassetteitem_detail-col3">
        <div>築10年</div>
        <div>10階建</div>
        </li>
        </ul>
        </div>
        </div>
        </div>
        </div>
        <div class="cassetteitem-item">
        </div>
        </div>
        """
        building_tag = self._get_tag(html)

        building_info = target._scrape_building(building_tag)

        assert building_info.name == "ビルディング"
        assert building_info.image_url == "https://example.com/image.jpg"
        assert building_info.address == "東京都どこか"
        assert building_info.accesses == ["ＪＲ中央線/東京駅 歩1分"]
        assert building_info.age == "築10年"
        assert building_info.floor == "10階建"
        assert building_info.room_infos == []

    def test_scrape_room(self, target: SuumoScraper) -> None:
        html = """
        <tbody>
        <tr class="js-cassette_link">
        <td class="cassetteitem_other-checkbox cassetteitem_other-checkbox--newarrival js-cassetteitem_checkbox">
        <input class="js-ikkatsuCB js-single_checkbox" id="bukken_0" name="bc" type="checkbox" value="99999999"/><label for="bc"> </label>
        </td>
        <td>
        <div class="casssetteitem_other-thumbnail js-view_gallery_images js-noContextMenu" data-imgs="https://example.com/image01.jpg,https://example.com/image02.jpg">
        <img alt="" class="casssetteitem_other-thumbnail-img casssetteitem_other-thumbnail-img--hasimages js-view_gallery-modal js-scrollLazy" rel="https://example.com/image01.jpg"/>
        <span class="cassetteitem_other-thumbnail-expansion js-view_gallery-modal"></span>
        </div>
        </td>
        <td>5階</td>
        <td>
        <ul>
        <li>
        <span class="cassetteitem_price cassetteitem_price--rent">
        <span class="cassetteitem_other-emphasis ui-text--bold">
        10万円
        </span>
        </span>
        </li>
        <li>
        <span class="cassetteitem_price cassetteitem_price--administration">
        5000円
        </span>
        </li>
        </ul>
        </td>
        <td>
        <ul>
        <li>
        <span class="cassetteitem_price cassetteitem_price--deposit">
        -
        </span>
        </li>
        <li>
        <span class="cassetteitem_price cassetteitem_price--gratuity">
        -
        </span>
        </li>
        </ul>
        </td>
        <td>
        <ul>
        <li><span class="cassetteitem_madori">1DK</span></li>
        <li>
        <span class="cassetteitem_menseki">40.0m<sup>2</sup></span>
        </li>
        </ul>
        </td>
        <td>
        <ul class="cassetteitem-taglist">
        <li><span class="cassetteitem-tag">パノラマ</span></li>
        </ul>
        </td>
        </tr>
        </tbody>
        """  # noqa
        room_tag = self._get_tag(html)

        room_info = target._scrape_room(room_tag)

        assert room_info.id == "99999999"
        assert room_info.image_urls == [
            "https://example.com/image01.jpg",
            "https://example.com/image02.jpg",
        ]
        assert room_info.floor == "5階"
        assert room_info.price_rent == "10万円"
        assert room_info.price_maintenance == "5000円"
        assert room_info.price_deposit == "-"
        assert room_info.price_gratuity == "-"
        assert room_info.section_type == "1DK"
        assert room_info.area == "40.0m2"


class TestRoomInfoRegister:
    @pytest.fixture
    def aws_credentials(self) -> None:
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    @pytest.fixture
    def target(self, aws_credentials: None) -> RoomInfoRegister:
        with mock_dynamodb():
            table_name = "testing"
            client = boto3.client("dynamodb", region_name="us-east-1")

            client.create_table(
                TableName=table_name,
                AttributeDefinitions=[
                    {
                        "AttributeName": "id",
                        "AttributeType": "S",
                    },
                ],
                KeySchema=[
                    {
                        "AttributeName": "id",
                        "KeyType": "HASH",
                    },
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            )

            register = RoomInfoRegister(
                building_infos=[
                    BuildingInfo(
                        name="ビル",
                        image_url="https://image.example.com",
                        address="住所",
                        accesses=["駅から徒歩1分"],
                        age="新築",
                        floor="10階",
                        room_infos=[
                            RoomInfo(
                                id="99999999",
                                image_urls=["https://example.com/image01.jpg"],
                                floor="5階",
                                price_rent="10万円",
                                price_maintenance="5000円",
                                price_deposit="-",
                                price_gratuity="-",
                                section_type="1DK",
                                area="40.0m2",
                            ),
                        ],
                    ),
                ],
                table_name=table_name,
            )
            yield register

            client.delete_table(TableName=table_name)

    def test_register(
        self,
        target: RoomInfoRegister,
        mocker: MockerFixture,
    ) -> None:
        mocked_register_room_info = mocker.patch.object(
            target, "_register_room_info"
        )

        target.register()

        mocked_register_room_info.assert_called_once_with(
            room_info=target.building_infos[0].room_infos[0],
            building_info=target.building_infos[0],
        )

    @pytest.mark.parametrize(
        ("registered_items", "expected_items"),
        [
            ([{"id": "99999999"}], 1),
            ([{"id": "11111111"}], 2),
        ],
    )
    def test_register_room_info(
        self,
        target: RoomInfoRegister,
        registered_items: typing.List[typing.Dict[str, typing.Any]],
        expected_items: int,
    ) -> None:
        with target.table.batch_writer() as writer:
            for item in registered_items:
                writer.put_item(Item=item)

        room_info = RoomInfo(
            id="99999999",
            image_urls=["https://example.com/image01.jpg"],
            floor="5階",
            price_rent="10万円",
            price_maintenance="5000円",
            price_deposit="-",
            price_gratuity="-",
            section_type="1DK",
            area="40.0m2",
        )
        building_info = BuildingInfo(
            name="ビル",
            image_url="https://image.example.com",
            address="住所",
            accesses=["駅から徒歩1分"],
            age="新築",
            floor="10階",
            room_infos=[room_info],
        )

        target._register_room_info(
            room_info=room_info,
            building_info=building_info,
        )

        res = target.table.scan()
        assert len(res["Items"]) == expected_items
