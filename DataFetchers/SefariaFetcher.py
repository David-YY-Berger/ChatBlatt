import requests

class SefariaFetcher:
    BASE_URL = "https://www.sefaria.org/api/texts"

    @staticmethod
    def fetch_talmud_daf(tractate: str, daf: str) -> dict:
        """
        Fetches the text of a single daf (folio) from Sefaria API.

        :param tractate: Name of the Talmudic tractate (e.g., "Berakhot")
        :param daf: Daf (folio) number in "2a", "2b", etc.
        :return: Dictionary containing Hebrew and English text
        """
        url = f"{SefariaFetcher.BASE_URL}/{tractate}.{daf}?context=0"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching {tractate} {daf}: {response.status_code}")
            return None

    @staticmethod
    def fetch_talmud_range(tractate: str, start_daf: str, end_daf: str) -> list:
        """
        Fetches multiple dafs from a start daf to an end daf.

        :param tractate: Name of the Talmudic tractate
        :param start_daf: Start daf (e.g., "2a")
        :param end_daf: End daf (e.g., "3b")
        :return: List of dictionaries containing daf texts
        """
        dafs = SefariaFetcher.generate_daf_range(start_daf, end_daf)
        return [SefariaFetcher.fetch_talmud_daf(tractate, daf) for daf in dafs]

    @staticmethod
    def print_talmud_daf(tractate: str, daf: str):
        """
        Fetches and prints a single daf in formatted output.

        :param tractate: Name of the Talmudic tractate
        :param daf: Daf (folio) number
        """
        data = SefariaFetcher.fetch_talmud_daf(tractate, daf)
        if data:
            print(f"\n=== {tractate} {daf} ===\n")
            print("📖 Hebrew Text:\n", "\n".join(data["he"]))
            print("\n📝 English Translation:\n", "\n".join(data["text"]))
            print("\n" + "="*40 + "\n")

    @staticmethod
    def print_talmud_range(tractate: str, start_daf: str, end_daf: str):
        """
        Fetches and prints multiple dafs in formatted output.

        :param tractate: Name of the Talmudic tractate
        :param start_daf: Start daf (e.g., "2a")
        :param end_daf: End daf (e.g., "3b")
        """
        dafs = SefariaFetcher.generate_daf_range(start_daf, end_daf)
        for daf in dafs:
            SefariaFetcher.print_talmud_daf(tractate, daf)

    @staticmethod
    def generate_daf_range(start_daf: str, end_daf: str) -> list:
        """
        Generates a range of dafs, considering both a/b pages.

        :param start_daf: Starting daf (e.g., "2a")
        :param end_daf: Ending daf (e.g., "3b")
        :return: List of daf references (e.g., ["2a", "2b", "3a", "3b"])
        """
        start_num = int(start_daf[:-1])
        start_side = start_daf[-1]

        end_num = int(end_daf[:-1])
        end_side = end_daf[-1]

        dafs = []
        for num in range(start_num, end_num + 1):
            if num == start_num and start_side == "b":
                dafs.append(f"{num}b")
            else:
                dafs.append(f"{num}a")
                dafs.append(f"{num}b")

        if end_side == "a":
            dafs.pop()  # Remove last "b" if end_daf is "a"

        return dafs

# Example Usage:
if __name__ == "__main__":
    SefariaFetcher.print_talmud_range("Berakhot", "2a", "3b")
