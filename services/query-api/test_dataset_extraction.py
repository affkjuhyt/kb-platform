"""
Test Dataset for Phase 6: Extraction Evaluation

This dataset provides realistic scenarios for evaluating the extraction pipeline.
Target: ≥80% extraction success rate
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional


@dataclass
class ExtractionTestCase:
    """A test case for extraction evaluation."""

    id: str
    name: str
    description: str
    query: str
    context: str
    schema: Dict[str, Any]
    expected_output: Dict[str, Any]
    difficulty: str  # easy, medium, hard
    category: str  # person, company, contract, product, etc.


# ============================================================================
# Test Dataset
# ============================================================================


def get_extraction_test_dataset() -> List[ExtractionTestCase]:
    """Get the complete extraction test dataset."""

    return [
        # Category: Person (Easy)
        ExtractionTestCase(
            id="person_001",
            name="Simple person extraction",
            description="Extract basic person information from clear text",
            query="Extract the person's name, age, and email",
            context="""
            John Smith is a software engineer at Google. He is 28 years old and graduated 
            from MIT in 2018. You can reach him at john.smith@google.com or visit his 
            office in Building 40. He joined the company in 2020 and works on the Cloud team.
            """,
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "email": {"type": "string"},
                },
                "required": ["name", "age"],
            },
            expected_output={
                "name": "John Smith",
                "age": 28,
                "email": "john.smith@google.com",
            },
            difficulty="easy",
            category="person",
        ),
        # Category: Person (Medium - multiple people)
        ExtractionTestCase(
            id="person_002",
            name="Multiple people extraction",
            description="Extract information about multiple people",
            query="Extract all team members with their roles and contact info",
            context="""
            Engineering Team:
            
            Sarah Johnson - Team Lead
            Email: sarah.j@company.com
            Phone: +1-555-0123
            Experience: 10 years
            
            Mike Chen - Senior Developer  
            Email: mike.chen@company.com
            Phone: +1-555-0124
            Experience: 5 years
            
            Emily Rodriguez - Junior Developer
            Email: emily.r@company.com
            Phone: +1-555-0125
            Experience: 1 year
            """,
            schema={
                "type": "object",
                "properties": {
                    "team_members": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                                "email": {"type": "string"},
                            },
                            "required": ["name", "role"],
                        },
                    },
                },
                "required": ["team_members"],
            },
            expected_output={
                "team_members": [
                    {
                        "name": "Sarah Johnson",
                        "role": "Team Lead",
                        "email": "sarah.j@company.com",
                    },
                    {
                        "name": "Mike Chen",
                        "role": "Senior Developer",
                        "email": "mike.chen@company.com",
                    },
                    {
                        "name": "Emily Rodriguez",
                        "role": "Junior Developer",
                        "email": "emily.r@company.com",
                    },
                ],
            },
            difficulty="medium",
            category="person",
        ),
        # Category: Company (Easy)
        ExtractionTestCase(
            id="company_001",
            name="Company information extraction",
            description="Extract company details from about page",
            query="Extract company name, founded year, headquarters, and employee count",
            context="""
            About TechCorp
            
            TechCorp was founded in 2005 by Jane Doe and John Smith in San Francisco, 
            California. The company has grown significantly over the past 19 years and 
            now employs over 5,000 people worldwide. Our headquarters remain in San 
            Francisco, with additional offices in New York, London, and Tokyo.
            
            TechCorp specializes in cloud computing solutions and enterprise software.
            """,
            schema={
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "founded_year": {"type": "integer"},
                    "headquarters": {"type": "string"},
                    "employees": {"type": "integer"},
                },
                "required": ["company_name", "founded_year"],
            },
            expected_output={
                "company_name": "TechCorp",
                "founded_year": 2005,
                "headquarters": "San Francisco, California",
                "employees": 5000,
            },
            difficulty="easy",
            category="company",
        ),
        # Category: Contract (Medium)
        ExtractionTestCase(
            id="contract_001",
            name="Contract details extraction",
            description="Extract key contract information",
            query="Extract contract parties, start date, end date, and value",
            context="""
            SERVICE AGREEMENT
            
            This Service Agreement ("Agreement") is entered into as of March 15, 2024 
            ("Effective Date") by and between:
            
            Client: Acme Corporation, a Delaware corporation with offices at 123 Main St
            Service Provider: CloudTech Solutions LLC, a California limited liability company
            
            Term: This Agreement shall commence on the Effective Date and continue for 
            a period of twelve (12) months, ending on March 14, 2025, unless terminated 
            earlier in accordance with the provisions herein.
            
            Contract Value: The total contract value is $150,000 USD, payable in monthly 
            installments of $12,500.
            
            Services: CloudTech shall provide managed cloud infrastructure services...
            """,
            schema={
                "type": "object",
                "properties": {
                    "contract_type": {"type": "string"},
                    "parties": {
                        "type": "object",
                        "properties": {
                            "client": {"type": "string"},
                            "service_provider": {"type": "string"},
                        },
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "value_usd": {"type": "number"},
                },
                "required": ["parties", "start_date"],
            },
            expected_output={
                "contract_type": "Service Agreement",
                "parties": {
                    "client": "Acme Corporation",
                    "service_provider": "CloudTech Solutions LLC",
                },
                "start_date": "2024-03-15",
                "end_date": "2025-03-14",
                "value_usd": 150000,
            },
            difficulty="medium",
            category="contract",
        ),
        # Category: Product (Easy)
        ExtractionTestCase(
            id="product_001",
            name="Product specifications",
            description="Extract product details from spec sheet",
            query="Extract product name, price, features, and availability",
            context="""
            Product: UltraBook Pro X1
            
            Specifications:
            - Processor: Intel Core i7-12700H
            - RAM: 32GB DDR5
            - Storage: 1TB NVMe SSD
            - Display: 15.6" 4K OLED
            
            Price: $2,499 USD
            Availability: In stock
            Warranty: 2 years
            
            Key Features:
            * All-day battery life (up to 14 hours)
            * Thunderbolt 4 ports (x2)
            * Wi-Fi 6E
            * Backlit keyboard
            
            Release Date: January 2024
            """,
            schema={
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "price_usd": {"type": "number"},
                    "availability": {"type": "string"},
                    "features": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["product_name", "price_usd"],
            },
            expected_output={
                "product_name": "UltraBook Pro X1",
                "price_usd": 2499,
                "availability": "In stock",
                "features": [
                    "All-day battery life (up to 14 hours)",
                    "Thunderbolt 4 ports (x2)",
                    "Wi-Fi 6E",
                    "Backlit keyboard",
                ],
            },
            difficulty="easy",
            category="product",
        ),
        # Category: Event (Medium)
        ExtractionTestCase(
            id="event_001",
            name="Event information extraction",
            description="Extract event details from announcement",
            query="Extract event name, date, location, and speakers",
            context="""
            ANNOUNCEMENT: Tech Summit 2024
            
            Join us for the annual Tech Summit on September 20-21, 2024, at the 
            Moscone Center in San Francisco, CA.
            
            Keynote Speakers:
            - Dr. Lisa Wang, CTO of FutureTech (Day 1, 9:00 AM)
            - James Miller, CEO of CloudScale (Day 1, 2:00 PM)
            - Dr. Aisha Patel, AI Research Director (Day 2, 10:00 AM)
            
            Topics: AI/ML, Cloud Computing, Cybersecurity
            
            Registration: $899 early bird, $1,199 regular
            Capacity: Limited to 2,000 attendees
            
            Contact: events@techsummit.com
            """,
            schema={
                "type": "object",
                "properties": {
                    "event_name": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "location": {"type": "string"},
                    "speakers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "registration_fee_usd": {"type": "number"},
                },
                "required": ["event_name", "start_date"],
            },
            expected_output={
                "event_name": "Tech Summit 2024",
                "start_date": "2024-09-20",
                "end_date": "2024-09-21",
                "location": "Moscone Center, San Francisco, CA",
                "speakers": [
                    "Dr. Lisa Wang, CTO of FutureTech",
                    "James Miller, CEO of CloudScale",
                    "Dr. Aisha Patel, AI Research Director",
                ],
                "registration_fee_usd": 899,
            },
            difficulty="medium",
            category="event",
        ),
        # Category: Financial (Hard)
        ExtractionTestCase(
            id="financial_001",
            name="Financial statement extraction",
            description="Extract financial metrics from report",
            query="Extract revenue, expenses, profit, and key financial ratios",
            context="""
            Q4 2023 Financial Report
            
            Revenue Performance:
            Total revenue for Q4 2023 reached $45.2 million, representing a 15% 
            increase year-over-year. Subscription revenue accounted for $32.1M, 
            while professional services contributed $13.1M.
            
            Cost Structure:
            Cost of goods sold (COGS): $18.5M
            Operating expenses: $12.3M
            - R&D: $5.2M
            - Sales & Marketing: $4.8M
            - G&A: $2.3M
            
            Profitability:
            Gross profit: $26.7M (59% gross margin)
            Operating profit: $14.4M (32% operating margin)
            Net income: $11.2M (25% net margin)
            
            EPS: $0.42 per share
            """,
            schema={
                "type": "object",
                "properties": {
                    "quarter": {"type": "string"},
                    "revenue_millions": {"type": "number"},
                    "expenses_millions": {"type": "number"},
                    "net_income_millions": {"type": "number"},
                    "gross_margin_percent": {"type": "number"},
                    "eps": {"type": "number"},
                },
                "required": ["quarter", "revenue_millions"],
            },
            expected_output={
                "quarter": "Q4 2023",
                "revenue_millions": 45.2,
                "expenses_millions": 30.8,
                "net_income_millions": 11.2,
                "gross_margin_percent": 59,
                "eps": 0.42,
            },
            difficulty="hard",
            category="financial",
        ),
        # Category: Address (Easy)
        ExtractionTestCase(
            id="address_001",
            name="Address extraction",
            description="Extract address information",
            query="Extract full address including street, city, state, zip, and country",
            context="""
            Shipping Address:
            
            1234 Market Street, Suite 500
            San Francisco, CA 94102
            United States
            
            Recipient: John Doe
            Phone: (415) 555-0123
            
            Delivery Instructions: Leave with receptionist
            """,
            schema={
                "type": "object",
                "properties": {
                    "street_address": {"type": "string"},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "zip_code": {"type": "string"},
                    "country": {"type": "string"},
                },
                "required": ["street_address", "city"],
            },
            expected_output={
                "street_address": "1234 Market Street, Suite 500",
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94102",
                "country": "United States",
            },
            difficulty="easy",
            category="address",
        ),
        # Category: Meeting (Medium)
        ExtractionTestCase(
            id="meeting_001",
            name="Meeting notes extraction",
            description="Extract meeting details and action items",
            query="Extract meeting date, attendees, key decisions, and action items",
            context="""
            MEETING MINUTES
            
            Date: March 20, 2024
            Time: 2:00 PM - 3:30 PM
            Location: Conference Room A
            
            Attendees:
            - Sarah Johnson (Product Manager)
            - Mike Chen (Lead Developer)
            - Emily Rodriguez (Designer)
            - Tom Wilson (QA Lead)
            
            Agenda: Q2 Roadmap Planning
            
            Key Decisions:
            1. Priority will be given to mobile app improvements
            2. New API version will be released in June
            3. Security audit scheduled for May
            
            Action Items:
            - Sarah: Finalize feature prioritization by March 25 [HIGH PRIORITY]
            - Mike: Prepare API documentation by April 5
            - Emily: Create mobile UI mockups by April 1
            - Tom: Update test automation suite by April 10
            
            Next Meeting: April 3, 2024
            """,
            schema={
                "type": "object",
                "properties": {
                    "meeting_date": {"type": "string"},
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "key_decisions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "assignee": {"type": "string"},
                                "task": {"type": "string"},
                                "due_date": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["meeting_date"],
            },
            expected_output={
                "meeting_date": "2024-03-20",
                "attendees": [
                    "Sarah Johnson (Product Manager)",
                    "Mike Chen (Lead Developer)",
                    "Emily Rodriguez (Designer)",
                    "Tom Wilson (QA Lead)",
                ],
                "key_decisions": [
                    "Priority will be given to mobile app improvements",
                    "New API version will be released in June",
                    "Security audit scheduled for May",
                ],
                "action_items": [
                    {
                        "assignee": "Sarah",
                        "task": "Finalize feature prioritization",
                        "due_date": "March 25",
                    },
                    {
                        "assignee": "Mike",
                        "task": "Prepare API documentation",
                        "due_date": "April 5",
                    },
                    {
                        "assignee": "Emily",
                        "task": "Create mobile UI mockups",
                        "due_date": "April 1",
                    },
                    {
                        "assignee": "Tom",
                        "task": "Update test automation suite",
                        "due_date": "April 10",
                    },
                ],
            },
            difficulty="medium",
            category="meeting",
        ),
        # Category: Job Posting (Medium)
        ExtractionTestCase(
            id="job_001",
            name="Job posting extraction",
            description="Extract job details from posting",
            query="Extract job title, company, location, salary, and requirements",
            context="""
            Senior Software Engineer
            
            Company: TechCorp Inc.
            Location: San Francisco, CA (Hybrid - 2 days in office)
            Employment Type: Full-time
            
            About the Role:
            We're looking for a Senior Software Engineer to join our Platform team.
            You'll be building scalable microservices that power our core product.
            
            Requirements:
            - 5+ years of experience in software engineering
            - Strong proficiency in Python and Go
            - Experience with Kubernetes and Docker
            - Bachelor's degree in Computer Science or equivalent
            
            Nice to Have:
            - Experience with PostgreSQL and Redis
            - Knowledge of gRPC and Protocol Buffers
            - Previous startup experience
            
            Compensation:
            - Salary: $160,000 - $200,000 per year
            - Equity: 0.1% - 0.25%
            - Benefits: Health, dental, vision, 401(k) matching
            
            Apply by: April 15, 2024
            """,
            schema={
                "type": "object",
                "properties": {
                    "job_title": {"type": "string"},
                    "company": {"type": "string"},
                    "location": {"type": "string"},
                    "salary_min": {"type": "number"},
                    "salary_max": {"type": "number"},
                    "requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["job_title", "company"],
            },
            expected_output={
                "job_title": "Senior Software Engineer",
                "company": "TechCorp Inc.",
                "location": "San Francisco, CA (Hybrid - 2 days in office)",
                "salary_min": 160000,
                "salary_max": 200000,
                "requirements": [
                    "5+ years of experience in software engineering",
                    "Strong proficiency in Python and Go",
                    "Experience with Kubernetes and Docker",
                    "Bachelor's degree in Computer Science or equivalent",
                ],
            },
            difficulty="medium",
            category="job",
        ),
    ]


def get_test_cases_by_category(category: str) -> List[ExtractionTestCase]:
    """Get test cases filtered by category."""
    return [tc for tc in get_extraction_test_dataset() if tc.category == category]


def get_test_cases_by_difficulty(difficulty: str) -> List[ExtractionTestCase]:
    """Get test cases filtered by difficulty."""
    return [tc for tc in get_extraction_test_dataset() if tc.difficulty == difficulty]


def export_test_dataset(filepath: str):
    """Export test dataset to JSON file."""
    dataset = get_extraction_test_dataset()
    data = [asdict(tc) for tc in dataset]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(dataset)} test cases to {filepath}")


# ============================================================================
# Statistics
# ============================================================================


def print_dataset_statistics():
    """Print statistics about the test dataset."""
    dataset = get_extraction_test_dataset()

    # By category
    categories = {}
    for tc in dataset:
        categories[tc.category] = categories.get(tc.category, 0) + 1

    # By difficulty
    difficulties = {}
    for tc in dataset:
        difficulties[tc.difficulty] = difficulties.get(tc.difficulty, 0) + 1

    print("=" * 60)
    print("EXTRACTION TEST DATASET STATISTICS")
    print("=" * 60)
    print(f"\nTotal test cases: {len(dataset)}")
    print(f"\nBy Category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    print(f"\nBy Difficulty:")
    for diff, count in sorted(difficulties.items()):
        print(f"  {diff}: {count}")
    print("\n" + "=" * 60)
    print("TARGET: ≥80% extraction success rate")
    print("=" * 60)


if __name__ == "__main__":
    print_dataset_statistics()

    # Optionally export
    # export_test_dataset("extraction_test_dataset.json")
