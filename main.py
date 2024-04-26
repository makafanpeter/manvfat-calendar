import os
import uuid
from datetime import datetime, timedelta
from typing import List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from icalendar import Calendar, Event, vText

load_dotenv('.env')


class MatchFixture:
    """Represents a fixture for a match between two teams."""

    def __init__(self, team: str, opponent: str, home: bool, date: str, time: str):
        """
        Initialize a MatchFixture object.

        Args:
            team (str): The name of the home team or one of the teams.
            opponent (str): The name of the away team or one of the teams.
            home (bool): True if 'team' is the home team, False otherwise.
            date (str): The date of the match in 'YYYY-MM-DD' format.
            time (str): The time of the match in 'HH:MM' format.
        """
        self.team = team
        self.opponent = opponent
        self.home = home
        self.datetime = self.__parse_datetime(date, time)

    @staticmethod
    def __parse_datetime(date: str, time: str) -> datetime:
        """
        Parse date and time strings into a datetime object.

        Args:
            date (str): The date of the match in 'YYYY-MM-DD' format.
            time (str): The time of the match in 'HH:MM' format.

        Returns:
            datetime: The datetime object representing the match date and time.
        """
        datetime_str = f"{date} {time}"
        return datetime.strptime(datetime_str, "%A %d %B %H:%M")

    def get_datetime(self) -> datetime:
        """
        Get the datetime object representing the match date and time.

        Returns:
            datetime: The datetime object.
        """
        return self.datetime

    def get_title(self) -> str:
        """
        Get the match title based on home/away status.

        Returns:
            str: The match title string.
        """
        if self.home:
            return f"{self.team} vs {self.opponent}"
        else:
            return f"{self.opponent} vs {self.team}"

    def __str__(self) -> str:
        """
        Return a string representation of the match fixture.

        Returns:
            str: A formatted string showing the match details.
        """
        return f"{self.get_title()} on {self.datetime.strftime('%m/%d/%Y %I:%M %p')}"


class ManVFatConnector:

    def __init__(self):
        self.page_url = os.environ['URL']
        self.team = os.environ['TEAM']

    def get_page_content(self):
        response = requests.get(self.page_url, headers=self.get_request_headers())
        response.raise_for_status()
        return response.text

    def __get_fixtures(self) -> List[{}]:
        match_fixtures = []
        page = self.get_page_content()
        soup = BeautifulSoup(page, 'html.parser')

        fixtures = soup.find('div', attrs={'id': 'upcomingfixtures'})
        if fixtures:
            upcoming_fixtures = fixtures.find_all('li')

            if upcoming_fixtures:
                for li in upcoming_fixtures:
                    # Date
                    date_element = li.find('h4')
                    # Team
                    team_element = li.find('div', attrs={'class': 'team text-right'})
                    if team_element:
                        team_element = team_element.find('span')
                    # Opponent
                    opponent_element = li.find('div', attrs={'class': 'team right text-left'})
                    if opponent_element:
                        opponent_element = opponent_element.find('span')
                    # Time
                    time_element = li.find('div', attrs={'class': 'schedule'})
                    if time_element:
                        match_time_elements = time_element.find_all('span', class_='match-time')
                        if len(match_time_elements) >= 2:
                            time_element = match_time_elements[1]

                    team, date, opponent, time = team_element.string, date_element.string, opponent_element.string, time_element.string
                    match = {"team": team, "date": date, "opponent": opponent, "time": time}
                    match_fixtures.append(match)

        return match_fixtures

    @staticmethod
    def get_request_headers():
        return {
            'Content-Type': 'application/text',
            'Accept': 'application/text',
            'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/121.0.0.0 Safari/537.36"
        }

    def get_team_fixtures(self) -> List[MatchFixture]:
        team_fixtures = []
        fixtures = self.__get_fixtures()
        for fixture in fixtures:
            if fixture['team'] == self.team:
                match = MatchFixture(fixture['team'], fixture['opponent'], True, fixture['date'], fixture['time'])
                team_fixtures.append(match)
            elif fixture['opponent'] == self.team:
                match = MatchFixture(fixture['team'], fixture['opponent'], False, fixture['date'], fixture['time'])
                team_fixtures.append(match)

        return team_fixtures


class ManVFatCalender:
    def __init__(self, team, location):
        self.cal = Calendar()
        self.cal.add('prodid', f'-//Man V Fat Calender Oldbury - {team}//manvfatfootball.org//')
        self.cal.add('version', '2.0')
        self.location = vText(location)

    def add_event(self, event: Event):
        if event:
            event['uid'] = str(uuid.uuid4())
            event['location'] = self.location
            self.cal.add_component(event)

    def export_calendar(self, file_name):
        with open(file_name, 'wb') as f:
            f.write(self.cal.to_ical())


class ManVFatCalendarExporter:
    def __init__(self, team, location, fixtures: List[MatchFixture]):
        self.location = location
        self.team = team
        self.export_path = os.environ.get("ExportPath")
        self.fixtures = fixtures

    def export_to_ical(self, filename: str):
        cal = ManVFatCalender(team=self.team, location=self.location)
        for fixture in self.fixtures:
            event = Event()
            event.add('name', fixture.get_title())
            event.add('description', fixture.__str__())
            event.add('dtstart', fixture.get_datetime())
            event.add('dtend', fixture.get_datetime() + timedelta(minutes=30))
            cal.add_event(event)

        directory = os.path.join(self.export_path, "MyCalendar")
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = os.path.join(directory, filename)
        cal.export_calendar(filename)


if __name__ == '__main__':
    man = ManVFatConnector()
    matches = man.get_team_fixtures()
    export = ManVFatCalendarExporter(man.team, "Portway Lifestyle Centre, Oldbury Birmingham, B69 1HE", matches)
    export.export_to_ical(f"MyCalendar.ics")
