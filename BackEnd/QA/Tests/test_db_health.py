import unittest

from numpy.ma.testutils import assert_equal

from BackEnd.DB.Collections import Collection, CollectionObjs
from BackEnd.DataPipeline.DBScriptParentClass import DBParentClass


class DatabaseHealthTests(DBParentClass):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        pass
        # super().tearDown() - this causes a failure (if all tests are run consecutively)... not sure why..

    ###########################################  Misc Tests ##################################################33

    def test_foo(self):
        # self.db_api.get_backup_mongo_dump()
        pass

    ###########################################  Source Tests ##################################################33

    def test_valid_num_sources(self):
        assert_equal(self.count_all_documents(CollectionObjs.BT), 12488)
        assert_equal(self.count_all_documents(CollectionObjs.TN), 1773)

    def test_sources_not_empty(self):
        collections = [
            CollectionObjs.TN,
            CollectionObjs.BT
        ]

        # Queries to check
        query_names = [
            "check_en_content_empty",
            "check_heb_content_empty",
            "check_key_empty",
            # "check_summary_empty"
        ]

        failures = []

        for collection in collections:
            for query_name in query_names:
                query = self.get_query(query_name)
                # Find all documents that **match the "empty" condition**
                results = self.db_api.execute_query_with_collection(
                    {
                        "operation": "find",
                        "filter": query
                    },
                    collection=collection
                )

                for doc in results:
                    key = doc.get("key", "<no key>")
                    print(f"[FAIL] Collection {collection.name}, Query {query_name}, Key: {key}")
                    failures.append((collection.name, query_name, key))

        if failures:
            # Fail the test at the end, summarizing all failures
            fail_messages = "\n".join(
                f"Collection {c}, Query {q}, Key {k}" for c, q, k in failures
            )
            self.fail(f"Some sources failed validation:\n{fail_messages}")

    def test_sources_valid_key(self):
        collections = [CollectionObjs.BT, CollectionObjs.TN]
        all_valid = True

        for col in collections:
            invalid_keys = self.get_invalid_keys(col)
            if invalid_keys:
                all_valid = False
                print(f"\nCollection '{col.name}' has invalid keys:")
                for key in invalid_keys:
                    print(f"  - {key}")

        assert all_valid, "Some documents have invalid key format!"

    def test_basic_functions_with_db(self):

        test_collection = CollectionObjs.TN #any random collection

        # Insert example data into collection
        data = {
            "key": "example_key",
            "content": "This is the content of the Talmud passage."
        }
        doc_id = self.db_api.insert(test_collection, data)
        # print(f"Inserted document ID: {doc_id}")

        # Query data
        query_results = self.db_api.execute_raw_query({
            "collection": test_collection,
            "filter": {"key": "example_key"}
        })
        # print(f"Query results: {query_results}")

        # Update data
        updated_rows = self.db_api.update(
            test_collection,
            {"key": "example_key"},
            {"content": "Updated content of the Talmud passage."}
        )
        # print(f"Updated {updated_rows} rows.")

        # Delete data
        deleted_rows = self.db_api.delete_instance(
            test_collection,
            {"key": "example_key"}
        )
        # print(f"Deleted {deleted_rows} rows.")

    def test_assert_collection_stats_unchanged(self):
        """
        Assert that collection statistics remain unchanged to ensure data integrity.
        This test will fail if the underlying data has been modified.
        Any html parsing changes will fail this func - FAISS indexes and LMM parsing on based on the html cleaning algo.
        """
        # todo add for hebrew content too..

        # Define expected baseline values for each collection
        expected_baselines = {
            CollectionObjs.BT: {
                'word_stats': {
                    'total_documents': 12488,
                    'valid_documents': 12488,
                    'average': 453.7,
                    'median': 358.5,
                    'p20': 163.0,
                    'p80': 696.0,
                    'min': 2,
                    'max': 3565,
                    'std_dev': 358.5
                },
                'char_stats': {
                    'total_documents': 12488,
                    'valid_documents': 12488,
                    'average': 2499.7,
                    'median': 1975.0,
                    'p20': 888.0,
                    'p80': 3822.0,
                    'min': 16,
                    'max': 19953,
                    'std_dev': 1987.1
                },
                'validation': {
                    'total_documents': 12488,
                    'clean_documents': 12488,
                    'documents_with_issues': 0,
                    'is_healthy': True
                }
            },
            CollectionObjs.TN: {
                'word_stats': {
                    'total_documents': 1773,
                    'valid_documents': 1773,
                    'average': 348.6,
                    'median': 174.0,
                    'p20': 84.0,
                    'p80': 467.6,
                    'min': 6,
                    'max': 7581,
                    'std_dev': 549.0
                },
                'char_stats': {
                    'total_documents': 1773,
                    'valid_documents': 1773,
                    'average': 1868.9,
                    'median': 923.0,
                    'p20': 444.4,
                    'p80': 2486.6,
                    'min': 30,
                    'max': 41328,
                    'std_dev': 2981.0
                },
                'validation': {
                    'total_documents': 1773,
                    'clean_documents': 1766,
                    'documents_with_issues': 7,
                    'is_healthy': True
                }
            }
        }

        # Track overall results
        all_passed = True
        failed_collections = []

        # Test each collection
        for collection, expected in expected_baselines.items():
            # Get actual stats once
            word_stats = self.get_avg_num_words_by_collection(collection)
            char_stats = self.get_avg_num_chars_by_collection(collection)
            validation = self.validate_clean_english_content(collection)

            # Print statistics using the actual values we just retrieved
            self._print_collection_stats_from_data(
                collection,
                word_stats,
                char_stats,
                validation
            )

            # Now assert the values match expected baseline
            print("\n" + "=" * 80)
            print(f"ASSERTING DATA INTEGRITY FOR: {collection.name}")
            print("=" * 80)

            try:
                # Assert each category matches
                self._assert_stats_match(
                    word_stats,
                    expected['word_stats'],
                    f"{collection.name} Word Stats"
                )
                self._assert_stats_match(
                    char_stats,
                    expected['char_stats'],
                    f"{collection.name} Char Stats"
                )
                self._assert_validation_match(
                    validation,
                    expected['validation'],
                    f"{collection.name} Validation"
                )

                print(f"✅ {collection.name} collection data integrity verified - all values match expected baseline")

            except AssertionError as e:
                print(f"❌ {collection.name} collection FAILED data integrity check:")
                print(f"   {str(e)}")
                all_passed = False
                failed_collections.append(collection.name)

        # Print final summary
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ ALL COLLECTIONS PASSED DATA INTEGRITY CHECKS")
            print(f"   Verified {len(expected_baselines)} collections successfully")
        else:
            print("❌ SOME COLLECTIONS FAILED DATA INTEGRITY CHECKS")
            print(f"   Failed collections: {', '.join(failed_collections)}")
            print(f"   Passed: {len(expected_baselines) - len(failed_collections)}/{len(expected_baselines)}")
        print("=" * 80)

        # Raise assertion if any failed
        if not all_passed:
            raise AssertionError(
                f"Data integrity check failed for {len(failed_collections)} collection(s): "
                f"{', '.join(failed_collections)}"
            )


    ############################################## Helper Functions ####################################################
    def count_all_documents(self, collection:Collection) -> int:
        query = self.get_query("count_all_documents")  # assumes queries are loaded in the class
        count = self.db_api.execute_query_with_collection(
            {
                "operation": "count_documents",
                "filter": query
            },
            collection=collection
        )
        return count

    def get_invalid_keys(self, collection: Collection) -> list[str]:
        """Return a list of keys that do not match the expected format."""
        results = self.db_api.execute_query_with_collection(
            {
                "operation": "find",
                "filter": self.get_query("check_key_format")
            },
            collection=collection
        )
        return [doc.get("key") for doc in results] if results else []

    def get_avg_num_words_by_collection(self, collection: Collection) -> dict:
        """
        Calculate word count statistics for the collection.

        Returns:
            dict: Statistics including average, percentiles, and data health metrics
        """
        src_content_lst = self.db_api.get_all_src_contents_of_collection(collection)

        if not src_content_lst:
            return {
                "average": 0,
                "median": 0,
                "p20": 0,
                "p80": 0,
                "min": 0,
                "max": 0,
                "total_documents": 0,
                "valid_documents": 0,
                "warnings": ["No documents found in collection"]
            }

        word_counts = []
        warnings = []

        for src in src_content_lst:
            try:
                # Get English content and clean it
                cleaned_text = src.get_clean_en_text()

                # Count words (split by whitespace)
                word_count = len(cleaned_text.split())
                word_counts.append(word_count)

                # Data health checks
                if word_count == 0:
                    warnings.append(f"Document {src.key} has 0 words after cleaning")
                elif word_count < 10:
                    warnings.append(f"Document {src.key} has very few words: {word_count}")

            except (IndexError, AttributeError) as e:
                warnings.append(f"Error processing document {src.key}: {str(e)}")
                continue

        if not word_counts:
            return {
                "average": 0,
                "median": 0,
                "p20": 0,
                "p80": 0,
                "min": 0,
                "max": 0,
                "total_documents": len(src_content_lst),
                "valid_documents": 0,
                "warnings": warnings + ["No valid word counts calculated"]
            }

        # Calculate statistics
        import numpy as np

        avg_words = np.mean(word_counts)
        median_words = np.median(word_counts)
        p20 = np.percentile(word_counts, 20)
        p80 = np.percentile(word_counts, 80)
        min_words = np.min(word_counts)
        max_words = np.max(word_counts)
        std_dev = np.std(word_counts)

        # Additional health checks
        if std_dev > avg_words * 2:
            warnings.append(f"High variability in word counts (std dev: {std_dev:.1f}, avg: {avg_words:.1f})")

        outlier_threshold = avg_words + 3 * std_dev
        outliers = [wc for wc in word_counts if wc > outlier_threshold]
        if outliers:
            warnings.append(f"Found {len(outliers)} potential outliers with very high word counts")

        return {
            "average": float(avg_words),
            "median": float(median_words),
            "p20": float(p20),
            "p80": float(p80),
            "min": int(min_words),
            "max": int(max_words),
            "std_dev": float(std_dev),
            "total_documents": len(src_content_lst),
            "valid_documents": len(word_counts),
            "warnings": warnings if warnings else None
        }

    def get_avg_num_chars_by_collection(self, collection: Collection) -> dict:
        """
        Calculate character count statistics for the collection.

        Returns:
            dict: Statistics including average, percentiles, and data health metrics
        """
        src_content_lst = self.db_api.get_all_src_contents_of_collection(collection)

        if not src_content_lst:
            return {
                "average": 0,
                "median": 0,
                "p20": 0,
                "p80": 0,
                "min": 0,
                "max": 0,
                "total_documents": 0,
                "valid_documents": 0,
                "warnings": ["No documents found in collection"]
            }

        char_counts = []
        warnings = []

        for src in src_content_lst:
            try:
                # Get English content and clean it
                cleaned_text = src.get_clean_en_text()

                # Count characters (excluding whitespace for meaningful count)
                char_count = len(cleaned_text)
                char_count_no_spaces = len(cleaned_text.replace(" ", "").replace("\n", "").replace("\t", ""))
                char_counts.append(char_count)

                # Data health checks
                if char_count == 0:
                    warnings.append(f"Document {src.key} has 0 characters after cleaning")
                elif char_count < 50:
                    warnings.append(f"Document {src.key} has very few characters: {char_count}")

                # Check for excessive whitespace
                if char_count > 0 and char_count_no_spaces / char_count < 0.7:
                    warnings.append(f"Document {src.key} has excessive whitespace (>30%)")

            except (IndexError, AttributeError) as e:
                warnings.append(f"Error processing document {src.key}: {str(e)}")
                continue

        if not char_counts:
            return {
                "average": 0,
                "median": 0,
                "p20": 0,
                "p80": 0,
                "min": 0,
                "max": 0,
                "total_documents": len(src_content_lst),
                "valid_documents": 0,
                "warnings": warnings + ["No valid character counts calculated"]
            }

        # Calculate statistics
        import numpy as np

        avg_chars = np.mean(char_counts)
        median_chars = np.median(char_counts)
        p20 = np.percentile(char_counts, 20)
        p80 = np.percentile(char_counts, 80)
        min_chars = np.min(char_counts)
        max_chars = np.max(char_counts)
        std_dev = np.std(char_counts)

        # Additional health checks
        if std_dev > avg_chars * 2:
            warnings.append(f"High variability in character counts (std dev: {std_dev:.1f}, avg: {avg_chars:.1f})")

        outlier_threshold = avg_chars + 3 * std_dev
        outliers = [cc for cc in char_counts if cc > outlier_threshold]
        if outliers:
            warnings.append(f"Found {len(outliers)} potential outliers with very high character counts")

        return {
            "average": float(avg_chars),
            "median": float(median_chars),
            "p20": float(p20),
            "p80": float(p80),
            "min": int(min_chars),
            "max": int(max_chars),
            "std_dev": float(std_dev),
            "total_documents": len(src_content_lst),
            "valid_documents": len(char_counts),
            "warnings": warnings if warnings else None
        }

    def validate_clean_english_content(self, collection: Collection) -> dict:
        """
        Validate that content is clean English text without HTML artifacts or problematic characters.

        Returns:
            dict: Validation results with issues found and recommendations
        """
        src_content_lst = self.db_api.get_all_src_contents_of_collection(collection)

        if not src_content_lst:
            return {
                "is_healthy": False,
                "total_documents": 0,
                "issues": ["No documents found in collection"]
            }

        issues = []
        document_issues = {}
        total_docs = len(src_content_lst)
        clean_docs = 0

        for src in src_content_lst:
            doc_issues = []

            try:
                cleaned_text = src.get_clean_en_text()

                # Check for HTML remnants
                html_indicators = ['<', '>', '&nbsp;', '&lt;', '&gt;', '&amp;']
                if any(indicator in cleaned_text for indicator in html_indicators):
                    doc_issues.append("Contains HTML remnants after cleaning")

                # Check for excessive special characters
                import re
                special_char_count = len(re.findall(r'[^a-zA-Z0-9\s.,!?;:\'\"-]', cleaned_text))
                if len(cleaned_text) > 0 and special_char_count / len(cleaned_text) > 0.05:
                    doc_issues.append(f"High special character ratio: {special_char_count}/{len(cleaned_text)}")

                # Check for control characters
                control_chars = [c for c in cleaned_text if ord(c) < 32 and c not in '\n\t\r']
                if control_chars:
                    doc_issues.append(f"Contains {len(control_chars)} control characters")

                # Check for excessive whitespace
                if re.search(r'\s{5,}', cleaned_text):
                    doc_issues.append("Contains excessive consecutive whitespace")

                # Check for non-ASCII characters (might be fine, but flag for review)
                non_ascii_count = sum(1 for c in cleaned_text if ord(c) > 127)
                if len(cleaned_text) > 0 and non_ascii_count / len(cleaned_text) > 0.1:
                    doc_issues.append(f"High non-ASCII character ratio: {non_ascii_count}/{len(cleaned_text)}")

                # Check for null bytes
                if '\x00' in cleaned_text:
                    doc_issues.append("Contains null bytes")

                # Check for proper sentence structure (basic check)
                if cleaned_text and not re.search(r'[.!?]', cleaned_text):
                    doc_issues.append("No sentence-ending punctuation found")

                # Check for reasonable word-to-character ratio
                words = cleaned_text.split()
                if words and len(cleaned_text) / len(words) > 20:
                    doc_issues.append("Unusually long average word length - possible encoding issues")

                if doc_issues:
                    document_issues[src.key] = doc_issues
                else:
                    clean_docs += 1

            except (IndexError, AttributeError) as e:
                doc_issues.append(f"Error processing: {str(e)}")
                document_issues[src.key] = doc_issues

        # Summary statistics
        issue_rate = (total_docs - clean_docs) / total_docs if total_docs > 0 else 0

        if issue_rate > 0.1:
            issues.append(f"High issue rate: {issue_rate * 100:.1f}% of documents have problems")

        return {
            "is_healthy": issue_rate < 0.05,  # Less than 5% with issues is considered healthy
            "total_documents": total_docs,
            "clean_documents": clean_docs,
            "documents_with_issues": total_docs - clean_docs,
            "issue_rate": f"{issue_rate * 100:.1f}%",
            "document_issues": document_issues if document_issues else None,
            "summary_issues": issues if issues else None,
            "recommendation": "Content is clean and ready for processing" if issue_rate < 0.05
            else "Review flagged documents and improve HTML cleaning process"
        }

    def _print_collection_stats_from_data(self, collection: Collection, word_stats: dict,
                                          char_stats: dict, validation: dict):
        """
        Print comprehensive statistics for a collection using pre-fetched data.

        Args:
            collection: The collection being analyzed
            word_stats: Pre-fetched word statistics
            char_stats: Pre-fetched character statistics
            validation: Pre-fetched validation results
        """
        print("\n" + "=" * 80)
        print(f"COLLECTION STATISTICS: {collection.name}")
        print("=" * 80)

        # Print Word Count Statistics
        print("\n📊 WORD COUNT STATISTICS")
        print("-" * 80)
        print(f"{'Metric':<20} {'Value':>15} {'Description':<40}")
        print("-" * 80)
        print(f"{'Total Documents':<20} {word_stats['total_documents']:>15,} {'Documents in collection':<40}")
        print(f"{'Valid Documents':<20} {word_stats['valid_documents']:>15,} {'Successfully processed':<40}")
        print(f"{'Average Words':<20} {word_stats['average']:>15,.1f} {'Mean word count per document':<40}")
        print(f"{'Median Words':<20} {word_stats['median']:>15,.1f} {'Middle value (50th percentile)':<40}")
        print(f"{'20th Percentile':<20} {word_stats['p20']:>15,.1f} {'80% of docs have more words':<40}")
        print(f"{'80th Percentile':<20} {word_stats['p80']:>15,.1f} {'80% of docs have fewer words':<40}")
        print(f"{'Minimum Words':<20} {word_stats['min']:>15,} {'Shortest document':<40}")
        print(f"{'Maximum Words':<20} {word_stats['max']:>15,} {'Longest document':<40}")
        print(f"{'Std Deviation':<20} {word_stats['std_dev']:>15,.1f} {'Variability in word counts':<40}")

        # Print Character Count Statistics
        print("\n📏 CHARACTER COUNT STATISTICS")
        print("-" * 80)
        print(f"{'Metric':<20} {'Value':>15} {'Description':<40}")
        print("-" * 80)
        print(f"{'Total Documents':<20} {char_stats['total_documents']:>15,} {'Documents in collection':<40}")
        print(f"{'Valid Documents':<20} {char_stats['valid_documents']:>15,} {'Successfully processed':<40}")
        print(f"{'Average Characters':<20} {char_stats['average']:>15,.1f} {'Mean character count per document':<40}")
        print(f"{'Median Characters':<20} {char_stats['median']:>15,.1f} {'Middle value (50th percentile)':<40}")
        print(f"{'20th Percentile':<20} {char_stats['p20']:>15,.1f} {'80% of docs have more characters':<40}")
        print(f"{'80th Percentile':<20} {char_stats['p80']:>15,.1f} {'80% of docs have fewer characters':<40}")
        print(f"{'Minimum Characters':<20} {char_stats['min']:>15,} {'Shortest document':<40}")
        print(f"{'Maximum Characters':<20} {char_stats['max']:>15,} {'Longest document':<40}")
        print(f"{'Std Deviation':<20} {char_stats['std_dev']:>15,.1f} {'Variability in character counts':<40}")

        # Print Content Quality Validation
        print("\n✅ CONTENT QUALITY VALIDATION")
        print("-" * 80)
        health_icon = "✅" if validation['is_healthy'] else "⚠️"
        print(f"{'Overall Health':<20} {health_icon:>15} {validation['recommendation']:<40}")
        print(f"{'Total Documents':<20} {validation['total_documents']:>15,} {'Documents analyzed':<40}")
        print(f"{'Clean Documents':<20} {validation['clean_documents']:>15,} {'No issues detected':<40}")
        print(f"{'Problem Documents':<20} {validation['documents_with_issues']:>15,} {'Require attention':<40}")
        print(f"{'Issue Rate':<20} {validation['issue_rate']:>15} {'Percentage with problems':<40}")

        # Print Warnings for Word Stats
        if word_stats.get('warnings'):
            print("\n⚠️  WORD COUNT WARNINGS")
            print("-" * 80)
            for i, warning in enumerate(word_stats['warnings'], 1):
                print(f"  {i}. {warning}")

        # Print Warnings for Character Stats
        if char_stats.get('warnings'):
            print("\n⚠️  CHARACTER COUNT WARNINGS")
            print("-" * 80)
            for i, warning in enumerate(char_stats['warnings'], 1):
                print(f"  {i}. {warning}")

        # Print Summary Issues from Validation
        if validation.get('summary_issues'):
            print("\n⚠️  VALIDATION SUMMARY ISSUES")
            print("-" * 80)
            for i, issue in enumerate(validation['summary_issues'], 1):
                print(f"  {i}. {issue}")

        # Print Specific Document Issues (limit to first 10 for readability)
        if validation.get('document_issues'):
            print("\n🔍 DOCUMENT-SPECIFIC ISSUES (First 10)")
            print("-" * 80)
            print(f"{'Document Key':<30} {'Issues':<50}")
            print("-" * 80)
            for i, (doc_key, issues) in enumerate(list(validation['document_issues'].items())[:10], 1):
                issues_str = "; ".join(issues)
                # Truncate if too long
                if len(issues_str) > 47:
                    issues_str = issues_str[:44] + "..."
                print(f"{doc_key:<30} {issues_str:<50}")

            if len(validation['document_issues']) > 10:
                print(f"\n... and {len(validation['document_issues']) - 10} more documents with issues")

        print("\n" + "=" * 80)
        print()

    def _assert_stats_match(self, actual: dict, expected: dict, label: str, tolerance: float = 0.1):
        """
        Assert that actual stats match expected stats within tolerance.

        Args:
            actual: Actual statistics dictionary
            expected: Expected statistics dictionary
            label: Label for error messages
            tolerance: Tolerance for float comparisons (default 0.1)
        """
        for key, expected_value in expected.items():
            actual_value = actual[key]

            if isinstance(expected_value, float):
                # For floats, allow small tolerance
                diff = abs(actual_value - expected_value)
                if diff > tolerance:
                    raise AssertionError(
                        f"{label} - {key}: expected {expected_value}, got {actual_value} (diff: {diff})"
                    )
            elif isinstance(expected_value, int):
                # For integers, must match exactly
                if actual_value != expected_value:
                    raise AssertionError(
                        f"{label} - {key}: expected {expected_value}, got {actual_value}"
                    )
            else:
                # For other types, use equality
                if actual_value != expected_value:
                    raise AssertionError(
                        f"{label} - {key}: expected {expected_value}, got {actual_value}"
                    )

        print(f"  ✓ {label} - all metrics match expected values")

    def _assert_validation_match(self, actual: dict, expected: dict, label: str):
        """
        Assert that validation results match expected values.

        Args:
            actual: Actual validation dictionary
            expected: Expected validation dictionary
            label: Label for error messages
        """
        for key, expected_value in expected.items():
            actual_value = actual[key]

            if actual_value != expected_value:
                raise AssertionError(
                    f"{label} - {key}: expected {expected_value}, got {actual_value}"
                )

        print(f"  ✓ {label} - validation results match expected values")

    ###################################################################

if __name__ == "__main__":
    unittest.main()