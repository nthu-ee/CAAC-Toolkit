import datetime


class Year:

    YEAR_BEGIN = 1911

    # the current A.C. year
    YEAR_CURRENT = datetime.datetime.now().year

    # the current Taiwan year
    YEAR_CURRENT_TAIWAN = YEAR_CURRENT - YEAR_BEGIN

    @classmethod
    def taiwanize(self, year):
        """Make the year into its Taiwan year representation."""

        return year - self.YEAR_BEGIN if year >= self.YEAR_BEGIN else year

    @classmethod
    def centuryze(self, year):
        """Make the year into its A.C. year representation."""

        return year + self.YEAR_BEGIN if year < self.YEAR_BEGIN else year
