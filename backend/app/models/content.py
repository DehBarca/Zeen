"""
Content document models for MongoDB
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ContentType(str, Enum):
    """Enum for content types"""
    MOVIE = "movie"
    SERIES = "series"
    EPISODE = "episode"


class Content:
    """MongoDB Content document (base class)"""
    
    def __init__(
        self,
        title: str,
        description: str,
        content_type: ContentType,
        duration_minutes: int,
        release_date: datetime,
        poster_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        rating: Optional[float] = None,
        genres: Optional[List[str]] = None,
        cast: Optional[List[str]] = None,
        directors: Optional[List[str]] = None,
        _id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self._id = _id
        self.title = title
        self.description = description
        self.content_type = content_type
        self.duration_minutes = duration_minutes
        self.release_date = release_date
        self.poster_url = poster_url
        self.banner_url = banner_url
        self.rating = rating or 0.0
        self.genres = genres or []
        self.cast = cast or []
        self.directors = directors or []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert content to dictionary"""
        return {
            "_id": self._id,
            "title": self.title,
            "description": self.description,
            "content_type": self.content_type.value if isinstance(self.content_type, ContentType) else self.content_type,
            "duration_minutes": self.duration_minutes,
            "release_date": self.release_date,
            "poster_url": self.poster_url,
            "banner_url": self.banner_url,
            "rating": self.rating,
            "genres": self.genres,
            "cast": self.cast,
            "directors": self.directors,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Movie(Content):
    """MongoDB Movie document"""
    
    def __init__(
        self,
        title: str,
        description: str,
        duration_minutes: int,
        release_date: datetime,
        video_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            title=title,
            description=description,
            content_type=ContentType.MOVIE,
            duration_minutes=duration_minutes,
            release_date=release_date,
            **kwargs
        )
        self.video_url = video_url
    
    def to_dict(self):
        data = super().to_dict()
        data["video_url"] = self.video_url
        return data


class Episode:
    """MongoDB Episode document"""
    
    def __init__(
        self,
        series_id: str,
        episode_number: int,
        season_number: int,
        title: str,
        duration_minutes: int,
        release_date: datetime,
        description: Optional[str] = None,
        video_url: Optional[str] = None,
        rating: Optional[float] = None,
        _id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self._id = _id
        self.series_id = series_id
        self.episode_number = episode_number
        self.season_number = season_number
        self.title = title
        self.description = description
        self.duration_minutes = duration_minutes
        self.release_date = release_date
        self.video_url = video_url
        self.rating = rating or 0.0
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self):
        return {
            "_id": self._id,
            "series_id": self.series_id,
            "episode_number": self.episode_number,
            "season_number": self.season_number,
            "title": self.title,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "release_date": self.release_date,
            "video_url": self.video_url,
            "rating": self.rating,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Series(Content):
    """MongoDB Series document"""
    
    def __init__(
        self,
        title: str,
        description: str,
        release_date: datetime,
        total_seasons: int = 0,
        total_episodes: int = 0,
        **kwargs
    ):
        super().__init__(
            title=title,
            description=description,
            content_type=ContentType.SERIES,
            duration_minutes=0,  # Series don't have a single duration
            release_date=release_date,
            **kwargs
        )
        self.total_seasons = total_seasons
        self.total_episodes = total_episodes
    
    def to_dict(self):
        data = super().to_dict()
        data["total_seasons"] = self.total_seasons
        data["total_episodes"] = self.total_episodes
        return data
