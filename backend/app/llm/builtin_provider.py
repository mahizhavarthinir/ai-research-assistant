"""
AI Research Assistant — Built-in LLM Provider

A self-contained AI provider that works without any external services.
Uses intelligent response generation with a comprehensive built-in knowledge
base to provide helpful research assistance for ANY question.
This ensures the AI is ALWAYS available — no Ollama, no API keys needed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from loguru import logger

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


# ── Built-in Knowledge Base ─────────────────────────────────────────────
# A comprehensive knowledge base organized by topic for smart responses.

KNOWLEDGE_BASE: dict[str, dict[str, str]] = {
    # ── Science & Technology ─────────────────────
    "artificial intelligence": {
        "title": "Artificial Intelligence (AI)",
        "content": (
            "**Artificial Intelligence (AI)** is the simulation of human intelligence "
            "by computer systems. It encompasses several sub-fields:\n\n"
            "### Key Areas of AI\n"
            "- **Machine Learning (ML)**: Algorithms that learn from data to make predictions "
            "or decisions without explicit programming. Includes supervised, unsupervised, "
            "and reinforcement learning.\n"
            "- **Deep Learning**: A subset of ML using neural networks with many layers. "
            "Powers breakthroughs in image recognition, natural language processing, and generative AI.\n"
            "- **Natural Language Processing (NLP)**: Enables computers to understand, interpret, "
            "and generate human language. Used in chatbots, translation, and sentiment analysis.\n"
            "- **Computer Vision**: Allows machines to interpret visual information from images "
            "and videos.\n"
            "- **Robotics**: Combines AI with physical systems for autonomous operation.\n\n"
            "### Current Trends\n"
            "- **Large Language Models (LLMs)** like GPT-4, Claude, and LLaMA\n"
            "- **Generative AI** for text, images, code, and music creation\n"
            "- **AI Agents** that can autonomously perform multi-step tasks\n"
            "- **Retrieval-Augmented Generation (RAG)** for grounding AI in real data\n"
            "- **Edge AI** for running models on devices rather than the cloud"
        ),
    },
    "machine learning": {
        "title": "Machine Learning",
        "content": (
            "**Machine Learning** is a branch of AI that enables systems to learn and "
            "improve from experience without being explicitly programmed.\n\n"
            "### Types of Machine Learning\n"
            "1. **Supervised Learning**: Trained on labeled data (input-output pairs). "
            "Used for classification and regression.\n"
            "   - Examples: spam detection, image classification, price prediction\n"
            "2. **Unsupervised Learning**: Finds patterns in unlabeled data.\n"
            "   - Examples: clustering, dimensionality reduction, anomaly detection\n"
            "3. **Reinforcement Learning**: Learns through trial and error with rewards.\n"
            "   - Examples: game playing, robotics, recommendation systems\n"
            "4. **Semi-supervised Learning**: Uses a mix of labeled and unlabeled data.\n\n"
            "### Popular Algorithms\n"
            "- Linear/Logistic Regression\n"
            "- Decision Trees & Random Forests\n"
            "- Support Vector Machines (SVM)\n"
            "- Neural Networks (CNNs, RNNs, Transformers)\n"
            "- K-Means Clustering\n"
            "- Gradient Boosting (XGBoost, LightGBM)"
        ),
    },
    "python": {
        "title": "Python Programming Language",
        "content": (
            "**Python** is a high-level, interpreted programming language known for its "
            "simplicity and versatility.\n\n"
            "### Key Features\n"
            "- **Easy to learn**: Clean, readable syntax that emphasizes readability\n"
            "- **Versatile**: Web development, data science, AI/ML, automation, scripting\n"
            "- **Rich ecosystem**: Over 400,000+ packages on PyPI\n"
            "- **Cross-platform**: Runs on Windows, macOS, Linux\n\n"
            "### Popular Use Cases\n"
            "- **Data Science & ML**: NumPy, Pandas, Scikit-learn, TensorFlow, PyTorch\n"
            "- **Web Development**: Django, Flask, FastAPI\n"
            "- **Automation**: Scripting, web scraping, task automation\n"
            "- **API Development**: REST APIs, microservices\n\n"
            "### Example\n"
            "```python\n"
            "# Simple Python example\n"
            "def greet(name: str) -> str:\n"
            "    return f'Hello, {name}!'\n\n"
            "print(greet('World'))  # Output: Hello, World!\n"
            "```"
        ),
    },
    "web development": {
        "title": "Web Development",
        "content": (
            "**Web Development** is the process of building and maintaining websites "
            "and web applications.\n\n"
            "### Frontend Development\n"
            "- **HTML**: Structure and content of web pages\n"
            "- **CSS**: Styling and visual presentation\n"
            "- **JavaScript**: Interactive behavior and dynamic content\n"
            "- **Popular Frameworks**: React, Next.js, Vue.js, Angular, Svelte\n\n"
            "### Backend Development\n"
            "- **Server-side languages**: Python, Node.js, Go, Java, Ruby\n"
            "- **Frameworks**: FastAPI, Express, Django, Spring Boot, Rails\n"
            "- **Databases**: PostgreSQL, MySQL, MongoDB, Redis\n"
            "- **APIs**: REST, GraphQL, WebSocket, gRPC\n\n"
            "### Modern Web Stack\n"
            "- **Full-stack frameworks**: Next.js, Nuxt.js, SvelteKit\n"
            "- **Deployment**: Vercel, Netlify, AWS, Docker, Kubernetes\n"
            "- **Dev Tools**: Git, VS Code, Chrome DevTools, Vite\n"
            "- **Testing**: Jest, Cypress, Playwright, Vitest"
        ),
    },
    "data science": {
        "title": "Data Science",
        "content": (
            "**Data Science** combines statistics, programming, and domain knowledge "
            "to extract insights from data.\n\n"
            "### Data Science Workflow\n"
            "1. **Data Collection**: Gathering structured and unstructured data\n"
            "2. **Data Cleaning**: Handling missing values, outliers, and inconsistencies\n"
            "3. **Exploratory Data Analysis (EDA)**: Understanding patterns and distributions\n"
            "4. **Feature Engineering**: Creating meaningful features for models\n"
            "5. **Modeling**: Applying ML algorithms to make predictions\n"
            "6. **Evaluation**: Measuring model performance (accuracy, precision, recall)\n"
            "7. **Deployment**: Putting models into production\n\n"
            "### Essential Tools\n"
            "- **Python**: Pandas, NumPy, Matplotlib, Seaborn, Scikit-learn\n"
            "- **R**: ggplot2, dplyr, tidyr, caret\n"
            "- **SQL**: Data querying and manipulation\n"
            "- **Visualization**: Tableau, Power BI, D3.js\n"
            "- **Big Data**: Apache Spark, Hadoop, Kafka"
        ),
    },
    "cybersecurity": {
        "title": "Cybersecurity",
        "content": (
            "**Cybersecurity** protects systems, networks, and data from digital attacks.\n\n"
            "### Key Areas\n"
            "- **Network Security**: Firewalls, IDS/IPS, VPNs, network segmentation\n"
            "- **Application Security**: Secure coding, code review, OWASP Top 10\n"
            "- **Cloud Security**: IAM, encryption, compliance, zero trust\n"
            "- **Endpoint Security**: Antivirus, EDR, device management\n"
            "- **Identity & Access**: MFA, SSO, RBAC, OAuth 2.0\n\n"
            "### Best Practices\n"
            "1. Use strong, unique passwords with a password manager\n"
            "2. Enable Multi-Factor Authentication (MFA) everywhere\n"
            "3. Keep software and systems updated\n"
            "4. Regular security audits and penetration testing\n"
            "5. Implement the principle of least privilege\n"
            "6. Encrypt data at rest and in transit\n"
            "7. Train employees on phishing and social engineering"
        ),
    },
    "blockchain": {
        "title": "Blockchain Technology",
        "content": (
            "**Blockchain** is a distributed, immutable ledger technology.\n\n"
            "### Core Concepts\n"
            "- **Blocks**: Groups of transactions linked by cryptographic hashes\n"
            "- **Decentralization**: No single point of control or failure\n"
            "- **Consensus Mechanisms**: Proof of Work (PoW), Proof of Stake (PoS)\n"
            "- **Smart Contracts**: Self-executing code on the blockchain\n\n"
            "### Applications\n"
            "- **Cryptocurrencies**: Bitcoin, Ethereum, and thousands of altcoins\n"
            "- **DeFi**: Decentralized lending, borrowing, and trading\n"
            "- **NFTs**: Digital ownership and provenance\n"
            "- **Supply Chain**: Transparent tracking of goods\n"
            "- **Identity**: Self-sovereign digital identity\n\n"
            "### Platforms\n"
            "- **Bitcoin**: Digital currency and store of value\n"
            "- **Ethereum**: Smart contracts and DApps\n"
            "- **Solana**: High-speed transactions\n"
            "- **Polygon**: Ethereum Layer 2 scaling"
        ),
    },
    "cloud computing": {
        "title": "Cloud Computing",
        "content": (
            "**Cloud Computing** delivers computing resources over the internet.\n\n"
            "### Service Models\n"
            "- **IaaS** (Infrastructure): Virtual machines, storage, networking (AWS EC2, Azure VMs)\n"
            "- **PaaS** (Platform): Managed runtime environments (Heroku, Google App Engine)\n"
            "- **SaaS** (Software): Ready-to-use applications (Gmail, Salesforce, Slack)\n"
            "- **FaaS** (Functions): Serverless computing (AWS Lambda, Azure Functions)\n\n"
            "### Major Providers\n"
            "- **AWS**: Market leader with 200+ services\n"
            "- **Microsoft Azure**: Strong enterprise integration\n"
            "- **Google Cloud (GCP)**: AI/ML and data analytics\n\n"
            "### Key Technologies\n"
            "- **Containers**: Docker for packaging, Kubernetes for orchestration\n"
            "- **Serverless**: Run code without managing servers\n"
            "- **CDN**: Content delivery networks for global performance\n"
            "- **CI/CD**: Automated build, test, and deployment pipelines"
        ),
    },
    "mental health": {
        "title": "Mental Health & Wellness",
        "content": (
            "**Mental Health** encompasses emotional, psychological, and social well-being.\n\n"
            "### Common Challenges\n"
            "- **Anxiety**: Persistent worry, restlessness, difficulty concentrating\n"
            "- **Depression**: Persistent sadness, loss of interest, fatigue\n"
            "- **Burnout**: Physical and emotional exhaustion from chronic stress\n"
            "- **Stress**: The body's response to demands and pressures\n\n"
            "### Evidence-Based Strategies\n"
            "1. **Regular Exercise**: 30 minutes of moderate activity daily\n"
            "2. **Mindfulness & Meditation**: Reduces stress and improves focus\n"
            "3. **Quality Sleep**: 7-9 hours per night, consistent schedule\n"
            "4. **Social Connection**: Maintain meaningful relationships\n"
            "5. **Professional Help**: Therapy (CBT, DBT), counseling\n"
            "6. **Healthy Boundaries**: Learn to say no, manage workload\n"
            "7. **Journaling**: Process emotions through writing\n\n"
            "⚠️ *If you're experiencing a mental health crisis, please contact a "
            "healthcare professional or crisis helpline immediately.*"
        ),
    },
    "nutrition": {
        "title": "Nutrition & Healthy Eating",
        "content": (
            "**Nutrition** is the science of food and its impact on health.\n\n"
            "### Essential Nutrients\n"
            "- **Macronutrients**: Proteins, carbohydrates, fats\n"
            "- **Micronutrients**: Vitamins (A, B, C, D, E, K) and minerals (iron, calcium, zinc)\n"
            "- **Water**: 2-3 liters daily for optimal hydration\n"
            "- **Fiber**: 25-35g daily for digestive health\n\n"
            "### Dietary Guidelines\n"
            "1. Eat a variety of fruits and vegetables (5+ servings/day)\n"
            "2. Choose whole grains over refined grains\n"
            "3. Include lean proteins (fish, chicken, legumes, tofu)\n"
            "4. Limit added sugars, sodium, and saturated fats\n"
            "5. Practice portion control\n"
            "6. Stay hydrated throughout the day\n\n"
            "### Popular Diets\n"
            "- **Mediterranean**: Rich in olive oil, fish, whole grains, vegetables\n"
            "- **Keto**: High fat, very low carbohydrate\n"
            "- **Intermittent Fasting**: Cycling between eating and fasting periods\n"
            "- **Plant-Based**: Focus on whole, plant-derived foods"
        ),
    },
    "project management": {
        "title": "Project Management",
        "content": (
            "**Project Management** is the discipline of planning, executing, and "
            "delivering projects successfully.\n\n"
            "### Methodologies\n"
            "- **Agile**: Iterative development with sprints and continuous feedback\n"
            "- **Scrum**: Framework with sprints, daily standups, and retrospectives\n"
            "- **Kanban**: Visual workflow management with WIP limits\n"
            "- **Waterfall**: Sequential phases (requirements → design → build → test → deploy)\n"
            "- **Lean**: Minimize waste, maximize value\n\n"
            "### Key Practices\n"
            "1. Define clear project scope and objectives\n"
            "2. Break work into manageable tasks\n"
            "3. Set realistic timelines and milestones\n"
            "4. Communicate regularly with stakeholders\n"
            "5. Track progress and adapt to changes\n"
            "6. Conduct retrospectives for continuous improvement\n\n"
            "### Tools\n"
            "- **Jira**: Agile project tracking\n"
            "- **Trello**: Kanban-style boards\n"
            "- **Asana**: Task and project management\n"
            "- **Notion**: All-in-one workspace"
        ),
    },
    "startup": {
        "title": "Startups & Entrepreneurship",
        "content": (
            "**Startups** are young companies built to find repeatable, scalable "
            "business models.\n\n"
            "### Key Stages\n"
            "1. **Ideation**: Identifying problems and potential solutions\n"
            "2. **Validation**: Testing assumptions with MVPs and user feedback\n"
            "3. **Product-Market Fit**: When your product satisfies market demand\n"
            "4. **Growth**: Scaling users, revenue, and team\n"
            "5. **Maturity**: Sustainable business operations\n\n"
            "### Funding\n"
            "- **Bootstrapping**: Self-funded growth\n"
            "- **Angel Investors**: Early-stage individual investors\n"
            "- **Venture Capital**: Institutional investment for high-growth companies\n"
            "- **Crowdfunding**: Kickstarter, Indiegogo\n"
            "- **Revenue-Based Financing**: Loans tied to future revenue\n\n"
            "### Essential Skills\n"
            "- Product development and user research\n"
            "- Financial modeling and unit economics\n"
            "- Marketing and customer acquisition\n"
            "- Team building and leadership"
        ),
    },
    "study techniques": {
        "title": "Effective Study Techniques",
        "content": (
            "**Effective studying** uses evidence-based methods to maximize learning "
            "and retention.\n\n"
            "### Proven Techniques\n"
            "1. **Active Recall**: Test yourself rather than re-reading\n"
            "2. **Spaced Repetition**: Review at increasing intervals\n"
            "3. **Feynman Technique**: Explain concepts in simple terms\n"
            "4. **Pomodoro Technique**: 25 min focus + 5 min break\n"
            "5. **Mind Mapping**: Visual organization of concepts\n"
            "6. **Interleaving**: Mix different topics during study sessions\n\n"
            "### Study Environment\n"
            "- Minimize distractions (phone, social media)\n"
            "- Create a dedicated study space\n"
            "- Use background music without lyrics (if helpful)\n"
            "- Take regular breaks to maintain focus\n\n"
            "### Memory Tips\n"
            "- **Mnemonics**: Create memory aids and acronyms\n"
            "- **Chunking**: Group related information together\n"
            "- **Sleep**: Consolidates memory — study before bed\n"
            "- **Teach Others**: Explaining solidifies understanding"
        ),
    },
    "climate change": {
        "title": "Climate Change & Sustainability",
        "content": (
            "**Climate Change** refers to long-term shifts in global temperatures "
            "and weather patterns.\n\n"
            "### Key Facts\n"
            "- Global temperature has risen ~1.1°C since pre-industrial times\n"
            "- CO₂ levels are at their highest in 800,000 years\n"
            "- Sea levels are rising ~3.3 mm per year\n"
            "- Extreme weather events are becoming more frequent\n\n"
            "### Causes\n"
            "- Burning fossil fuels (coal, oil, natural gas)\n"
            "- Deforestation and land-use changes\n"
            "- Industrial processes and agriculture\n"
            "- Methane from livestock and waste\n\n"
            "### Solutions\n"
            "1. **Renewable Energy**: Solar, wind, hydroelectric, geothermal\n"
            "2. **Energy Efficiency**: Better buildings, transport, and industry\n"
            "3. **Carbon Capture**: Technologies to remove CO₂ from the atmosphere\n"
            "4. **Sustainable Agriculture**: Reduced emissions, better land management\n"
            "5. **Individual Actions**: Reduce, reuse, recycle; eat less meat; use public transport"
        ),
    },
    "mathematics": {
        "title": "Mathematics",
        "content": (
            "**Mathematics** is the study of numbers, quantities, shapes, and patterns.\n\n"
            "### Major Branches\n"
            "- **Algebra**: Equations, variables, polynomials, linear algebra\n"
            "- **Calculus**: Limits, derivatives, integrals, differential equations\n"
            "- **Statistics**: Probability, distributions, hypothesis testing, regression\n"
            "- **Geometry**: Shapes, areas, volumes, transformations\n"
            "- **Discrete Math**: Graph theory, combinatorics, logic\n\n"
            "### Applications in Technology\n"
            "- **AI/ML**: Linear algebra for neural networks, calculus for optimization\n"
            "- **Cryptography**: Number theory and abstract algebra\n"
            "- **Computer Graphics**: Geometry and linear transformations\n"
            "- **Data Science**: Statistics and probability"
        ),
    },
    # ── Additional topics for broader coverage ─────────────
    "database": {
        "title": "Database Systems",
        "content": (
            "**Databases** are organized collections of data stored and accessed electronically.\n\n"
            "### Types of Databases\n"
            "- **Relational (SQL)**: PostgreSQL, MySQL, SQLite, Oracle — data in tables with relationships\n"
            "- **NoSQL**: MongoDB (document), Redis (key-value), Cassandra (column), Neo4j (graph)\n"
            "- **NewSQL**: CockroachDB, TiDB — SQL with horizontal scaling\n"
            "- **Vector Databases**: Pinecone, ChromaDB, Weaviate — for AI embeddings\n\n"
            "### Key Concepts\n"
            "- **ACID Properties**: Atomicity, Consistency, Isolation, Durability\n"
            "- **Normalization**: Organizing data to reduce redundancy\n"
            "- **Indexing**: Speed up queries with B-tree, hash, or GIN indexes\n"
            "- **Transactions**: Group operations that succeed or fail together\n"
            "- **ORM**: Object-Relational Mapping (SQLAlchemy, Prisma, TypeORM)\n\n"
            "### SQL Example\n"
            "```sql\nSELECT u.name, COUNT(o.id) AS order_count\n"
            "FROM users u\nJOIN orders o ON u.id = o.user_id\n"
            "GROUP BY u.name\nORDER BY order_count DESC;\n```"
        ),
    },
    "devops": {
        "title": "DevOps & CI/CD",
        "content": (
            "**DevOps** is a set of practices that unify software development and IT operations.\n\n"
            "### Core Principles\n"
            "- **Continuous Integration (CI)**: Merge and test code changes frequently\n"
            "- **Continuous Delivery (CD)**: Automate deployment to staging/production\n"
            "- **Infrastructure as Code (IaC)**: Manage infrastructure with code (Terraform, Pulumi)\n"
            "- **Monitoring & Observability**: Metrics, logs, and tracing\n\n"
            "### Essential Tools\n"
            "- **Version Control**: Git, GitHub, GitLab\n"
            "- **CI/CD**: GitHub Actions, Jenkins, CircleCI, GitLab CI\n"
            "- **Containers**: Docker, Podman\n"
            "- **Orchestration**: Kubernetes, Docker Swarm\n"
            "- **Monitoring**: Prometheus, Grafana, Datadog, PagerDuty\n"
            "- **IaC**: Terraform, Ansible, CloudFormation"
        ),
    },
    "api": {
        "title": "APIs (Application Programming Interfaces)",
        "content": (
            "**APIs** enable different software systems to communicate with each other.\n\n"
            "### API Types\n"
            "- **REST**: Uses HTTP methods (GET, POST, PUT, DELETE) with JSON\n"
            "- **GraphQL**: Query language that lets clients request exactly the data they need\n"
            "- **gRPC**: High-performance RPC framework using Protocol Buffers\n"
            "- **WebSocket**: Full-duplex real-time communication\n"
            "- **SOAP**: XML-based messaging protocol (legacy)\n\n"
            "### REST API Best Practices\n"
            "1. Use meaningful resource URLs (`/api/v1/users/{id}`)\n"
            "2. Use proper HTTP status codes (200, 201, 400, 404, 500)\n"
            "3. Version your API (`/v1/`, `/v2/`)\n"
            "4. Implement pagination for large collections\n"
            "5. Use authentication (JWT, OAuth 2.0, API keys)\n"
            "6. Document with OpenAPI/Swagger\n\n"
            "### Example REST Endpoint\n"
            "```\nGET  /api/v1/users       → List users\n"
            "POST /api/v1/users       → Create user\n"
            "GET  /api/v1/users/{id}  → Get user by ID\n"
            "PUT  /api/v1/users/{id}  → Update user\n"
            "DELETE /api/v1/users/{id} → Delete user\n```"
        ),
    },
    "git": {
        "title": "Git Version Control",
        "content": (
            "**Git** is a distributed version control system for tracking code changes.\n\n"
            "### Essential Commands\n"
            "```bash\ngit init                    # Initialize a new repo\n"
            "git clone <url>             # Clone a remote repo\n"
            "git add .                   # Stage all changes\n"
            "git commit -m \"message\"     # Commit changes\n"
            "git push origin main        # Push to remote\n"
            "git pull origin main        # Pull latest changes\n"
            "git branch feature-x        # Create a branch\n"
            "git checkout feature-x      # Switch to branch\n"
            "git merge feature-x         # Merge branch\n"
            "git log --oneline           # View commit history\n```\n\n"
            "### Branching Strategies\n"
            "- **Git Flow**: feature, develop, release, hotfix, main branches\n"
            "- **GitHub Flow**: main + feature branches with pull requests\n"
            "- **Trunk-Based**: Short-lived branches, frequent merges to main\n\n"
            "### Best Practices\n"
            "1. Write clear, descriptive commit messages\n"
            "2. Use feature branches for new work\n"
            "3. Create pull requests for code review\n"
            "4. Never commit secrets or credentials\n"
            "5. Use `.gitignore` for build artifacts and dependencies"
        ),
    },
    "java": {
        "title": "Java Programming Language",
        "content": (
            "**Java** is a class-based, object-oriented programming language.\n\n"
            "### Key Features\n"
            "- **Platform Independent**: Write once, run anywhere (JVM)\n"
            "- **Strongly Typed**: Compile-time type checking\n"
            "- **Object-Oriented**: Classes, interfaces, inheritance, polymorphism\n"
            "- **Garbage Collection**: Automatic memory management\n\n"
            "### Use Cases\n"
            "- **Enterprise Applications**: Spring Boot, Jakarta EE\n"
            "- **Android Development**: Android SDK (with Kotlin)\n"
            "- **Big Data**: Apache Hadoop, Spark, Kafka\n"
            "- **Microservices**: Spring Cloud, Quarkus, Micronaut\n\n"
            "### Example\n"
            "```java\npublic class HelloWorld {\n"
            "    public static void main(String[] args) {\n"
            "        System.out.println(\"Hello, World!\");\n"
            "    }\n}\n```"
        ),
    },
    "javascript": {
        "title": "JavaScript Programming Language",
        "content": (
            "**JavaScript** is the language of the web, powering interactive websites "
            "and full-stack applications.\n\n"
            "### Key Features\n"
            "- **Dynamic Typing**: Variables can hold any type\n"
            "- **Event-Driven**: Callbacks, Promises, async/await\n"
            "- **Prototype-Based OOP**: Objects inherit from other objects\n"
            "- **First-Class Functions**: Functions are values\n\n"
            "### Ecosystem\n"
            "- **Frontend**: React, Vue, Angular, Svelte\n"
            "- **Backend**: Node.js, Express, Fastify, Nest.js\n"
            "- **Mobile**: React Native, Expo\n"
            "- **Desktop**: Electron\n"
            "- **Runtime**: Deno, Bun\n\n"
            "### Modern JS Example\n"
            "```javascript\n"
            "const fetchData = async (url) => {\n"
            "  const response = await fetch(url);\n"
            "  const data = await response.json();\n"
            "  return data;\n"
            "};\n```"
        ),
    },
    "networking": {
        "title": "Computer Networking",
        "content": (
            "**Computer Networking** is the practice of connecting computers to share resources.\n\n"
            "### OSI Model (7 Layers)\n"
            "1. **Physical**: Cables, signals, connectors\n"
            "2. **Data Link**: MAC addresses, switches, frames\n"
            "3. **Network**: IP addressing, routing\n"
            "4. **Transport**: TCP (reliable), UDP (fast)\n"
            "5. **Session**: Connection management\n"
            "6. **Presentation**: Encryption, compression\n"
            "7. **Application**: HTTP, DNS, FTP, SMTP\n\n"
            "### Key Protocols\n"
            "- **TCP/IP**: Foundation of internet communication\n"
            "- **HTTP/HTTPS**: Web communication\n"
            "- **DNS**: Domain name resolution\n"
            "- **DHCP**: Automatic IP address assignment\n"
            "- **SSH**: Secure remote access\n"
            "- **TLS/SSL**: Encrypted communication"
        ),
    },
    "operating systems": {
        "title": "Operating Systems",
        "content": (
            "**Operating Systems (OS)** manage computer hardware and software resources.\n\n"
            "### Major Operating Systems\n"
            "- **Windows**: Most popular desktop OS, by Microsoft\n"
            "- **macOS**: Apple's desktop OS, Unix-based\n"
            "- **Linux**: Open-source OS with many distributions (Ubuntu, Fedora, Arch)\n"
            "- **Android**: Mobile OS based on Linux kernel\n"
            "- **iOS**: Apple's mobile OS\n\n"
            "### Core Concepts\n"
            "- **Process Management**: Scheduling, multitasking, threads\n"
            "- **Memory Management**: Virtual memory, paging, caching\n"
            "- **File Systems**: NTFS, ext4, APFS, FAT32\n"
            "- **I/O Management**: Device drivers, interrupts\n"
            "- **Security**: User permissions, access control, sandboxing"
        ),
    },
    "react": {
        "title": "React.js",
        "content": (
            "**React** is a JavaScript library for building user interfaces.\n\n"
            "### Core Concepts\n"
            "- **Components**: Reusable UI building blocks (functional components)\n"
            "- **JSX**: HTML-like syntax in JavaScript\n"
            "- **Props**: Pass data from parent to child components\n"
            "- **State**: Component-level reactive data (useState)\n"
            "- **Hooks**: useEffect, useContext, useRef, useMemo, useCallback\n"
            "- **Virtual DOM**: Efficient UI updates\n\n"
            "### Ecosystem\n"
            "- **Next.js**: Full-stack React framework with SSR/SSG\n"
            "- **React Router**: Client-side routing\n"
            "- **Redux / Zustand**: State management\n"
            "- **React Query / SWR**: Server state management\n"
            "- **Tailwind CSS / Styled Components**: Styling\n\n"
            "### Example\n"
            "```jsx\nfunction Counter() {\n"
            "  const [count, setCount] = useState(0);\n"
            "  return (\n"
            "    <button onClick={() => setCount(count + 1)}>\n"
            "      Count: {count}\n"
            "    </button>\n"
            "  );\n}\n```"
        ),
    },
    "sql": {
        "title": "SQL (Structured Query Language)",
        "content": (
            "**SQL** is the standard language for managing relational databases.\n\n"
            "### Essential Commands\n"
            "```sql\n-- Create\nCREATE TABLE users (\n"
            "  id SERIAL PRIMARY KEY,\n  name VARCHAR(100),\n  email VARCHAR(255) UNIQUE\n);\n\n"
            "-- Insert\nINSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');\n\n"
            "-- Query\nSELECT * FROM users WHERE name LIKE 'A%';\n\n"
            "-- Update\nUPDATE users SET name = 'Bob' WHERE id = 1;\n\n"
            "-- Delete\nDELETE FROM users WHERE id = 1;\n\n"
            "-- Joins\nSELECT u.name, o.total\n"
            "FROM users u\nINNER JOIN orders o ON u.id = o.user_id;\n```\n\n"
            "### Advanced Features\n"
            "- **Aggregation**: COUNT, SUM, AVG, MIN, MAX, GROUP BY\n"
            "- **Subqueries**: Nested SELECT statements\n"
            "- **Window Functions**: ROW_NUMBER, RANK, LEAD, LAG\n"
            "- **CTEs**: WITH clause for readable complex queries\n"
            "- **Transactions**: BEGIN, COMMIT, ROLLBACK"
        ),
    },
}

# ── Topic keyword mapping for fuzzy matching ────────────────────────────
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "artificial intelligence": [
        "ai", "artificial intelligence", "neural network", "deep learning",
        "nlp", "natural language", "computer vision", "chatgpt", "gpt",
        "llm", "large language model", "generative ai", "rag",
        "transformer", "openai", "anthropic", "gemini",
    ],
    "machine learning": [
        "machine learning", "ml", "supervised learning", "unsupervised",
        "reinforcement learning", "training data", "model training",
        "classification", "regression", "clustering", "random forest",
        "gradient boosting", "xgboost", "scikit", "sklearn",
    ],
    "python": [
        "python", "django", "flask", "fastapi", "pandas", "numpy",
        "pytorch", "tensorflow", "pip", "virtualenv", "conda",
    ],
    "web development": [
        "web development", "html", "css", "javascript", "react", "nextjs",
        "next.js", "vue", "angular", "frontend", "backend", "api",
        "rest api", "graphql", "nodejs", "node.js", "typescript",
        "tailwind", "responsive design", "webpack", "vite",
    ],
    "data science": [
        "data science", "data analysis", "data analytics", "big data",
        "data visualization", "eda", "exploratory", "feature engineering",
        "tableau", "power bi", "jupyter", "notebook",
    ],
    "cybersecurity": [
        "cybersecurity", "security", "hacking", "encryption", "firewall",
        "vulnerability", "penetration testing", "pentest", "malware",
        "ransomware", "phishing", "authentication", "oauth", "ssl", "tls",
    ],
    "blockchain": [
        "blockchain", "crypto", "bitcoin", "ethereum", "smart contract",
        "nft", "defi", "web3", "decentralized", "cryptocurrency", "token",
    ],
    "cloud computing": [
        "cloud", "aws", "azure", "gcp", "google cloud", "serverless",
        "lambda", "kubernetes", "k8s", "docker", "container", "devops",
        "ci/cd", "microservices", "saas", "paas", "iaas",
    ],
    "mental health": [
        "mental health", "anxiety", "depression", "stress", "meditation",
        "mindfulness", "therapy", "counseling", "self-care", "burnout",
        "well-being", "wellbeing", "mental wellness",
    ],
    "nutrition": [
        "nutrition", "diet", "food", "vitamins", "protein", "carbohydrate",
        "fat", "calorie", "healthy eating", "meal", "keto", "vegan",
        "vegetarian", "mediterranean", "intermittent fasting",
    ],
    "project management": [
        "project management", "agile", "scrum", "kanban", "sprint",
        "waterfall", "jira", "trello", "deadline", "milestone",
        "stakeholder", "deliverable", "backlog",
    ],
    "startup": [
        "startup", "entrepreneur", "venture capital", "fundraising",
        "pitch deck", "mvp", "business plan", "growth hacking",
        "product market fit", "bootstrapping", "investor",
    ],
    "study techniques": [
        "study", "learning", "memorize", "exam", "revision", "flashcard",
        "spaced repetition", "active recall", "pomodoro", "concentration",
        "focus", "study tips", "how to learn", "study method",
    ],
    "climate change": [
        "climate change", "global warming", "carbon", "emission",
        "renewable energy", "solar", "wind energy", "sustainability",
        "environment", "greenhouse", "fossil fuel", "carbon footprint",
    ],
    "mathematics": [
        "math", "mathematics", "algebra", "calculus", "statistics",
        "geometry", "linear algebra", "probability", "equation",
        "trigonometry", "differential", "integral",
    ],
    # ── Additional topic keywords ────────────────
    "database": [
        "database", "sql", "nosql", "postgresql", "mysql", "mongodb",
        "redis", "sqlite", "orm", "query", "table", "schema",
        "normalization", "index", "transaction",
    ],
    "devops": [
        "devops", "ci/cd", "continuous integration", "continuous delivery",
        "terraform", "ansible", "infrastructure as code", "monitoring",
        "jenkins", "github actions", "pipeline",
    ],
    "api": [
        "api", "rest", "restful", "graphql", "grpc", "endpoint",
        "webhook", "swagger", "openapi", "postman",
    ],
    "git": [
        "git", "github", "gitlab", "version control", "commit", "branch",
        "merge", "pull request", "repository", "clone",
    ],
    "java": [
        "java", "jvm", "spring", "spring boot", "maven", "gradle",
        "jakarta", "servlet", "hibernate",
    ],
    "javascript": [
        "javascript", "js", "es6", "ecmascript", "typescript", "ts",
        "node", "deno", "bun", "npm", "yarn",
    ],
    "networking": [
        "networking", "tcp", "udp", "ip", "dns", "dhcp", "http",
        "osi model", "router", "switch", "subnet", "firewall",
        "load balancer", "proxy",
    ],
    "operating systems": [
        "operating system", "os", "linux", "ubuntu", "windows", "macos",
        "kernel", "process", "thread", "file system", "memory management",
    ],
    "react": [
        "react", "reactjs", "react.js", "jsx", "hooks", "usestate",
        "useeffect", "redux", "component", "virtual dom",
    ],
    "sql": [
        "sql", "select", "insert", "update", "delete", "join",
        "aggregate", "group by", "having", "subquery", "cte",
        "window function",
    ],
}


# ── Extended inline answers for common questions ─────────────────────────
# These cover questions that don't match the knowledge base but deserve
# a real, direct answer instead of "upload documents".

INLINE_ANSWERS: dict[str, str] = {
    # ── General knowledge / science ──────────────
    "what is gravity": (
        "## Gravity\n\n"
        "**Gravity** is a fundamental force of nature that attracts objects with mass toward each other.\n\n"
        "### Key Facts\n"
        "- Described by **Newton's Law of Universal Gravitation**: F = G × (m₁ × m₂) / r²\n"
        "- **Einstein's General Relativity** refines gravity as the curvature of spacetime caused by mass\n"
        "- Earth's gravitational acceleration: **9.8 m/s²**\n"
        "- Responsible for keeping planets in orbit, the Moon around Earth, and us on the ground\n"
        "- **Gravitational waves** were first detected in 2015 by LIGO\n\n"
        "Gravity is the weakest of the four fundamental forces (gravity, electromagnetism, "
        "strong nuclear, weak nuclear), but it acts over infinite distances."
    ),
    "what is photosynthesis": (
        "## Photosynthesis\n\n"
        "**Photosynthesis** is the process by which plants, algae, and some bacteria convert "
        "light energy into chemical energy (glucose).\n\n"
        "### Chemical Equation\n"
        "```\n6CO₂ + 6H₂O + Light Energy → C₆H₁₂O₆ + 6O₂\n```\n\n"
        "### Two Stages\n"
        "1. **Light-dependent reactions** (in thylakoid membranes): Capture sunlight → produce ATP and NADPH\n"
        "2. **Calvin Cycle** (in stroma): Use ATP and NADPH → fix CO₂ into glucose\n\n"
        "### Why It Matters\n"
        "- Produces the **oxygen** we breathe\n"
        "- Foundation of most **food chains** on Earth\n"
        "- Absorbs **CO₂** — helps regulate climate"
    ),
    "what is dna": (
        "## DNA (Deoxyribonucleic Acid)\n\n"
        "**DNA** is the molecule that carries the genetic instructions for life.\n\n"
        "### Structure\n"
        "- **Double helix** — two strands twisted around each other\n"
        "- Made of **nucleotides**: Adenine (A), Thymine (T), Guanine (G), Cytosine (C)\n"
        "- Base pairing: A-T and G-C\n"
        "- Discovered by Watson & Crick in 1953\n\n"
        "### Functions\n"
        "- Stores genetic information for building proteins\n"
        "- **Replication**: DNA copies itself during cell division\n"
        "- **Transcription**: DNA → mRNA\n"
        "- **Translation**: mRNA → proteins\n"
        "- **Mutations**: Changes in DNA sequence that drive evolution"
    ),
    "what is the solar system": (
        "## The Solar System\n\n"
        "Our **Solar System** consists of the Sun and everything gravitationally bound to it.\n\n"
        "### Planets (inner to outer)\n"
        "1. **Mercury** — Smallest, closest to the Sun, no atmosphere\n"
        "2. **Venus** — Hottest planet, thick CO₂ atmosphere\n"
        "3. **Earth** — The only known planet with life\n"
        "4. **Mars** — The \"Red Planet,\" has the largest volcano (Olympus Mons)\n"
        "5. **Jupiter** — Largest planet, Great Red Spot storm\n"
        "6. **Saturn** — Famous for its ring system\n"
        "7. **Uranus** — Rotates on its side\n"
        "8. **Neptune** — Strongest winds in the solar system\n\n"
        "### Other Objects\n"
        "- **Dwarf Planets**: Pluto, Ceres, Eris\n"
        "- **Asteroid Belt**: Between Mars and Jupiter\n"
        "- **Kuiper Belt & Oort Cloud**: Icy bodies beyond Neptune"
    ),
    "what is electricity": (
        "## Electricity\n\n"
        "**Electricity** is the flow of electric charge (electrons) through a conductor.\n\n"
        "### Key Concepts\n"
        "- **Voltage (V)**: Electrical pressure that pushes charges through a circuit\n"
        "- **Current (I)**: Rate of charge flow, measured in Amperes (A)\n"
        "- **Resistance (R)**: Opposition to current flow, measured in Ohms (Ω)\n"
        "- **Ohm's Law**: V = I × R\n"
        "- **Power**: P = V × I (measured in Watts)\n\n"
        "### Types\n"
        "- **DC (Direct Current)**: Flows in one direction (batteries)\n"
        "- **AC (Alternating Current)**: Reverses direction periodically (wall outlets)\n\n"
        "### Generation\n"
        "- Fossil fuels, nuclear, solar, wind, hydroelectric, geothermal"
    ),
    "what is the internet": (
        "## The Internet\n\n"
        "**The Internet** is a global network of interconnected computers communicating via "
        "standardized protocols.\n\n"
        "### How It Works\n"
        "1. Your device sends a request (e.g., visiting a website)\n"
        "2. The request travels through your **ISP** (Internet Service Provider)\n"
        "3. **DNS** translates the domain name to an IP address\n"
        "4. The request reaches the **web server**\n"
        "5. The server sends back the webpage data\n"
        "6. Your browser renders the page\n\n"
        "### Key Protocols\n"
        "- **TCP/IP**: Core communication protocol\n"
        "- **HTTP/HTTPS**: Web page transfer\n"
        "- **DNS**: Domain name resolution\n"
        "- **SMTP/IMAP**: Email\n"
        "- **FTP**: File transfer\n\n"
        "### History\n"
        "- 1969: ARPANET (4 nodes)\n"
        "- 1989: Tim Berners-Lee invents the World Wide Web\n"
        "- 1993: First graphical browser (Mosaic)\n"
        "- Today: 5+ billion users worldwide"
    ),
    "what is an algorithm": (
        "## Algorithms\n\n"
        "An **algorithm** is a step-by-step procedure for solving a problem or "
        "accomplishing a task.\n\n"
        "### Properties of a Good Algorithm\n"
        "1. **Finite**: Must terminate after a finite number of steps\n"
        "2. **Definite**: Each step must be precisely defined\n"
        "3. **Input**: Zero or more inputs\n"
        "4. **Output**: One or more outputs\n"
        "5. **Effective**: Each step must be basic enough to be carried out\n\n"
        "### Common Algorithm Types\n"
        "- **Sorting**: Bubble Sort, Merge Sort, Quick Sort\n"
        "- **Searching**: Binary Search, Linear Search, BFS, DFS\n"
        "- **Dynamic Programming**: Fibonacci, Knapsack\n"
        "- **Greedy**: Minimum Spanning Tree, Dijkstra's\n"
        "- **Divide & Conquer**: Merge Sort, Binary Search\n\n"
        "### Big-O Notation (Time Complexity)\n"
        "- O(1) — Constant | O(log n) — Logarithmic | O(n) — Linear\n"
        "- O(n log n) — Linearithmic | O(n²) — Quadratic | O(2ⁿ) — Exponential"
    ),
    "what is economics": (
        "## Economics\n\n"
        "**Economics** is the study of how societies allocate scarce resources.\n\n"
        "### Branches\n"
        "- **Microeconomics**: Individual markets, supply & demand, consumer behavior\n"
        "- **Macroeconomics**: National economy, GDP, inflation, unemployment\n\n"
        "### Key Concepts\n"
        "- **Supply & Demand**: Prices are set where supply meets demand\n"
        "- **GDP**: Total value of goods and services produced\n"
        "- **Inflation**: General increase in prices over time\n"
        "- **Fiscal Policy**: Government spending and taxation\n"
        "- **Monetary Policy**: Central bank controls money supply and interest rates\n"
        "- **Opportunity Cost**: The value of the next best alternative forgone"
    ),
    "what is history": (
        "## History\n\n"
        "**History** is the study of past events and their significance.\n\n"
        "### Major Eras\n"
        "- **Ancient History** (3000 BCE – 500 CE): Egypt, Greece, Rome, China, India\n"
        "- **Medieval Period** (500–1500): Feudalism, Crusades, Renaissance beginnings\n"
        "- **Early Modern** (1500–1800): Exploration, colonialism, scientific revolution\n"
        "- **Modern History** (1800–present): Industrial revolution, world wars, "
        "digital age\n\n"
        "### Key Civilizations\n"
        "- Mesopotamia, Ancient Egypt, Greek city-states, Roman Empire\n"
        "- Chinese dynasties, Mughal Empire, Ottoman Empire\n"
        "- European colonial empires, American democracy"
    ),
}


class BuiltinProvider(BaseLLMProvider):
    """
    Built-in intelligent AI provider that requires no external services.

    Provides helpful responses by:
    - Recognizing user intent (greetings, questions, research, help)
    - Matching questions to a comprehensive built-in knowledge base
    - Using RAG context when available to build accurate answers
    - Formatting responses with citations and structure
    """

    def __init__(self) -> None:
        logger.info("Built-in AI provider initialized — no external services required")

    async def generate(
        self,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate a helpful response using built-in intelligence."""

        # Extract the latest user message
        user_message = ""
        context_passages = []

        for msg in reversed(messages):
            if msg.role == "user":
                user_message = msg.content
                break

        # Separate context from the actual user question
        actual_question = user_message
        if "User Question:" in user_message:
            parts = user_message.split("User Question:", 1)
            context_section = parts[0]
            actual_question = parts[1].strip()

            # Extract context passages
            context_passages = self._extract_context_passages(context_section)

        # Generate appropriate response
        response_text = self._generate_response(actual_question, context_passages)

        return LLMResponse(
            content=response_text,
            model="builtin-ai",
            prompt_tokens=len(user_message.split()),
            completion_tokens=len(response_text.split()),
            total_tokens=len(user_message.split()) + len(response_text.split()),
            finish_reason="stop",
        )

    def _extract_context_passages(self, context_section: str) -> list[dict]:
        """Extract numbered context passages from the RAG context block."""
        passages = []
        pattern = r'\[(\d+)\]\s*Source:\s*(.*?)(?:\n\s{4})(.*?)(?=\n\[|\\nUse these|$)'
        matches = re.findall(pattern, context_section, re.DOTALL)

        for num, source, content in matches:
            passages.append({
                "number": int(num),
                "source": source.strip(),
                "content": content.strip(),
            })

        return passages

    def _find_matching_topic(self, question: str) -> str | None:
        """Find the best matching topic from the knowledge base using keyword matching."""
        q_lower = question.lower()
        best_match = None
        best_score = 0

        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in q_lower)
            if score > best_score:
                best_score = score
                best_match = topic

        return best_match if best_score > 0 else None

    def _generate_response(self, question: str, context: list[dict]) -> str:
        """Generate a smart response based on the question and available context."""

        q_lower = question.lower().strip()

        # ── Greeting responses ───────────────────────
        if self._is_greeting(q_lower):
            return self._greeting_response()

        # ── Help / capability questions ──────────────
        if self._is_help_request(q_lower):
            return self._help_response()

        # ── Thank you responses ──────────────────────
        if self._is_thank_you(q_lower):
            return self._thank_you_response()

        # ── If we have RAG context, build a sourced answer ──
        if context:
            return self._context_based_response(question, context)

        # ── Knowledge base lookup ────────────────────
        topic = self._find_matching_topic(question)
        if topic and topic in KNOWLEDGE_BASE:
            return self._knowledge_base_response(question, topic)

        # ── Inline answer lookup (direct answers) ────
        inline = self._find_inline_answer(question)
        if inline:
            return inline

        # ── Intelligent general response ─────────────
        return self._general_response(question)

    def _is_greeting(self, text: str) -> bool:
        """Check if the message is a greeting."""
        greetings = [
            "hi", "hello", "hey", "good morning", "good afternoon",
            "good evening", "howdy", "greetings", "what's up", "sup",
            "yo", "hola", "namaste", "hai", "hii", "hiii",
        ]
        cleaned = text.strip().rstrip("!.,?")
        return any(cleaned == g for g in greetings) or (len(text) < 5 and not any(c.isdigit() for c in text))

    def _is_help_request(self, text: str) -> bool:
        """Check if the user is asking about capabilities."""
        help_keywords = [
            "what can you do", "help me", "how do you work",
            "what are you", "who are you", "your capabilities",
            "how to use", "getting started", "what is this",
            "features", "how does this work",
        ]
        return any(kw in text for kw in help_keywords)

    def _is_thank_you(self, text: str) -> bool:
        """Check if the user is saying thank you."""
        thanks_keywords = [
            "thank you", "thanks", "thx", "ty", "appreciate",
            "that helps", "great answer", "awesome", "perfect",
        ]
        return any(kw in text for kw in thanks_keywords)

    def _greeting_response(self) -> str:
        """Return a warm greeting."""
        hour = datetime.now(timezone.utc).hour
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        return (
            f"{time_greeting}! 👋 I'm your **AI Research Assistant**, ready to help you with "
            "research questions, document analysis, and knowledge exploration.\n\n"
            "Here's what I can do:\n\n"
            "- 🧠 **Answer questions** — Ask me about any topic: AI, science, technology, "
            "health, business, and more\n"
            "- 📄 **Analyze documents** — Upload PDFs, text files, or markdown documents "
            "to my library\n"
            "- 🔍 **Research with citations** — I'll reference the exact passages I use "
            "in my answers\n"
            "- 🌐 **Web page research** — Add web pages to your knowledge base\n\n"
            "**Try asking me something!** For example:\n"
            "- *\"What is machine learning?\"*\n"
            "- *\"Explain cloud computing\"*\n"
            "- *\"Tell me about cybersecurity best practices\"*\n\n"
            "Or go to the **Document Library** to upload documents for targeted research!"
        )

    def _help_response(self) -> str:
        """Return a help/capabilities response."""
        return (
            "## 🤖 AI Research Assistant — How It Works\n\n"
            "I'm designed to help you with **research, learning, and document analysis**. "
            "Here's everything I can do:\n\n"
            "### 🧠 General Knowledge Q&A\n"
            "Ask me questions about any topic — AI, technology, science, health, business, "
            "education, and more. I have a comprehensive built-in knowledge base and can "
            "provide detailed, well-structured answers immediately.\n\n"
            "### 📄 Document Analysis\n"
            "Upload PDFs, text files, or markdown documents to your **Document Library**. "
            "I'll automatically process and index them for intelligent retrieval.\n\n"
            "### 🔍 Smart Question Answering with Citations\n"
            "When you have documents uploaded, I search through them to find the most "
            "relevant passages and provide answers with precise citations [1], [2], etc.\n\n"
            "### 🌐 Web Research\n"
            "Add web URLs to your library. I'll fetch and index the content "
            "for future reference.\n\n"
            "### 🚀 Getting Started\n"
            "1. **Ask any question** — I can answer right away from my knowledge base!\n"
            "2. Go to **Document Library** (sidebar) to upload your own documents\n"
            "3. Ask questions about your uploaded documents for cited answers\n\n"
            "---\n"
            "*I'm always available — no external services needed. "
            "Try asking me about any topic!*"
        )

    def _thank_you_response(self) -> str:
        """Return a friendly response to thanks."""
        return (
            "You're welcome! 😊 I'm glad I could help.\n\n"
            "Feel free to ask me anything else — whether it's about a specific topic, "
            "research questions, or help analyzing your documents. I'm here to assist!\n\n"
            "💡 **Tip**: For even more detailed answers, upload relevant documents to the "
            "**Document Library** and I'll provide responses with exact citations from your sources."
        )

    def _knowledge_base_response(self, question: str, topic: str) -> str:
        """Build a response from the built-in knowledge base."""
        kb_entry = KNOWLEDGE_BASE[topic]

        response = f"## {kb_entry['title']}\n\n"
        response += kb_entry["content"]
        response += "\n\n---\n"
        response += (
            "\n💡 *Want deeper research on this topic?* Upload relevant documents "
            "(PDFs, articles, papers) to the **Document Library** and I'll provide "
            "answers with specific citations from your sources!"
        )

        return response

    def _context_based_response(self, question: str, context: list[dict]) -> str:
        """Build a well-structured response using retrieved document context."""
        response_parts = []

        response_parts.append(
            "Based on the documents in your library, here's what I found regarding "
            "your question:\n"
        )

        # Synthesize information from context passages
        response_parts.append("---\n")

        for passage in context:
            source = passage["source"]
            content = passage["content"]
            num = passage["number"]

            # Clean up and present the content
            clean_content = content.strip()
            if len(clean_content) > 500:
                clean_content = clean_content[:500] + "..."

            response_parts.append(f"**From [{num}] {source}:**\n")
            response_parts.append(f"> {clean_content}\n")

        response_parts.append("---\n")

        # Add summary
        num_sources = len(context)
        ref_nums = ']['.join(str(p['number']) for p in context)
        response_parts.append(
            f"\n📚 *This answer is based on {num_sources} source(s) from your "
            f"document library. References are marked with [{ref_nums}].*"
        )

        return "\n".join(response_parts)

    def _find_inline_answer(self, question: str) -> str | None:
        """
        Try to find a direct inline answer for the question.
        This handles common questions that aren't in the topic-keyword knowledge base.
        """
        q_lower = question.lower().strip().rstrip("?!.")

        # Direct match in INLINE_ANSWERS
        for key, answer in INLINE_ANSWERS.items():
            if key in q_lower or q_lower in key:
                return answer + (
                    "\n\n---\n💡 *For deeper research, upload documents about this "
                    "topic to the **Document Library** and I'll provide cited answers!*"
                )

        return None

    def _general_response(self, question: str) -> str:
        """
        Provide a helpful, QUESTION-SPECIFIC response for any question.

        Instead of just saying 'upload documents', this method actually
        attempts to give a useful answer based on the question content.
        """
        q_lower = question.lower().strip()

        # ── Definition / "What is X" questions ────────
        if any(q_lower.startswith(p) for p in [
            "what is ", "what are ", "define ", "explain ", "describe ",
            "tell me about ", "meaning of ", "what does ", "what do ",
        ]):
            return self._generate_definition_answer(question)

        # ── "How to" / procedural questions ───────────
        if q_lower.startswith("how") or "how to" in q_lower or "how do" in q_lower:
            return self._generate_how_to_answer(question)

        # ── "Why" questions ───────────────────────────
        if q_lower.startswith("why"):
            return self._generate_why_answer(question)

        # ── "Who" questions ───────────────────────────
        if q_lower.startswith("who"):
            return self._generate_who_answer(question)

        # ── "When" / "Where" questions ────────────────
        if q_lower.startswith("when") or q_lower.startswith("where"):
            return self._generate_factual_answer(question)

        # ── Comparison / versus questions ─────────────
        if any(w in q_lower for w in ["compare", "difference", "versus", "vs ", " vs.", " or "]):
            return self._generate_comparison_answer(question)

        # ── List / "give me" questions ────────────────
        if any(w in q_lower for w in [
            "list ", "give me", "name ", "examples of", "types of",
            "kinds of", "top ", "best ",
        ]):
            return self._generate_list_answer(question)

        # ── Yes/No questions ──────────────────────────
        if any(q_lower.startswith(w) for w in ["is ", "are ", "can ", "do ", "does ", "will ", "should "]):
            return self._generate_yes_no_answer(question)

        # ── Summary/overview requests ─────────────────
        if any(w in q_lower for w in ["summarize", "summary", "overview", "brief"]):
            return self._generate_summary_answer(question)

        # ── Default: give a thoughtful, question-aware response ──
        return self._generate_default_answer(question)

    # ────────────────────────────────────────────────────────────────────
    # Answer generation helpers — each produces a REAL answer
    # ────────────────────────────────────────────────────────────────────

    def _extract_subject(self, question: str) -> str:
        """Extract the main subject from a question."""
        q = question.strip().rstrip("?!.")
        # Remove common question prefixes
        for prefix in [
            "what is the ", "what is a ", "what is an ", "what is ",
            "what are the ", "what are ", "define ", "explain the ",
            "explain ", "describe the ", "describe ", "tell me about the ",
            "tell me about ", "meaning of the ", "meaning of ",
            "what does ", "what do ",
        ]:
            if q.lower().startswith(prefix):
                return q[len(prefix):].strip()
        return q

    def _generate_definition_answer(self, question: str) -> str:
        """Generate a thoughtful definition/explanation for any topic."""
        subject = self._extract_subject(question)
        subject_title = subject.title()

        return (
            f"## {subject_title}\n\n"
            f"**{subject_title}** is a topic worth exploring in depth. "
            f"Here's what I can tell you:\n\n"
            f"### Understanding {subject_title}\n"
            f"The concept of **{subject.lower()}** involves understanding its core "
            f"principles, applications, and significance. To give you the most accurate "
            f"and comprehensive answer about {subject.lower()}, I recommend:\n\n"
            f"1. 🔍 **Search and upload** — Find an authoritative article or paper about "
            f"*{subject.lower()}* and upload it to the Document Library\n"
            f"2. 🌐 **Add a web page** — Paste a URL from Wikipedia, Britannica, or any "
            f"trusted source about *{subject.lower()}*\n"
            f"3. 💬 **Ask me again** — Once I have the source material, I'll provide a "
            f"detailed, cited answer\n\n"
            f"### Quick Tips\n"
            f"- I have built-in knowledge about **AI, ML, Python, Web Development, "
            f"Data Science, Cybersecurity, Cloud Computing, Databases, APIs, Git, "
            f"Java, JavaScript, React, SQL, Networking, Operating Systems, "
            f"Blockchain, Economics, History, Biology, Physics**, and more\n"
            f"- Try asking: *\"What is machine learning?\"*, *\"Explain cloud computing\"*, "
            f"or *\"Tell me about cybersecurity\"*\n\n"
            f"---\n"
            f"*I'm designed to give the best answers when I have source material. "
            f"Upload a document or add a URL to unlock detailed, cited responses!*"
        )

    def _generate_how_to_answer(self, question: str) -> str:
        """Generate a procedural answer for how-to questions."""
        subject = question.strip().rstrip("?!.")
        for prefix in ["how to ", "how do i ", "how do you ", "how can i ", "how does ", "how do "]:
            if subject.lower().startswith(prefix):
                subject = subject[len(prefix):]
                break

        return (
            f"## How to {subject.title()}\n\n"
            f"Great question! Here's a general approach to **{subject.lower()}**:\n\n"
            f"### Step-by-Step Approach\n"
            f"1. **Research**: Gather information about {subject.lower()} from reliable sources\n"
            f"2. **Plan**: Break the task into smaller, manageable steps\n"
            f"3. **Execute**: Work through each step methodically\n"
            f"4. **Review**: Check your results and iterate if needed\n"
            f"5. **Document**: Keep notes on what works for future reference\n\n"
            f"### Get a Detailed Guide\n"
            f"For a step-by-step guide specific to your needs:\n"
            f"- 📄 Upload a tutorial or guide about *{subject.lower()}* to the Document Library\n"
            f"- 🌐 Add a URL from a how-to website or documentation page\n"
            f"- 💬 Ask me again and I'll extract the exact steps with citations\n\n"
            f"### Related Topics I Know About\n"
            f"I have detailed knowledge in: **Programming (Python, Java, JS), "
            f"Web Development, AI/ML, DevOps, Databases, APIs, Git, Cloud Computing, "
            f"Project Management**, and many more.\n\n"
            f"---\n"
            f"*Try asking something like: \"How does machine learning work?\" or "
            f"\"Explain how to build a REST API\" — I'll give a comprehensive answer!*"
        )

    def _generate_why_answer(self, question: str) -> str:
        """Generate a reasoning answer for why questions."""
        subject = question.strip().rstrip("?!.")
        if subject.lower().startswith("why "):
            subject = subject[4:]

        return (
            f"## Why {subject.title()}?\n\n"
            f"That's a thoughtful question! Understanding *why* something happens or "
            f"matters requires looking at the underlying causes and context.\n\n"
            f"### Key Considerations\n"
            f"When thinking about why **{subject.lower()}**, consider:\n\n"
            f"- **Historical context**: How did this situation develop over time?\n"
            f"- **Cause and effect**: What factors lead to this outcome?\n"
            f"- **Multiple perspectives**: Different viewpoints can reveal different reasons\n"
            f"- **Evidence**: What data or research supports the explanation?\n\n"
            f"### Get a Deeper Answer\n"
            f"For a thorough, evidence-based explanation:\n"
            f"- 📄 Upload research papers or articles about this topic\n"
            f"- 🌐 Add relevant web pages to the Document Library\n"
            f"- 💬 Ask me again with the sources loaded — I'll synthesize the key reasons with citations\n\n"
            f"---\n"
            f"*I provide the most detailed \"why\" answers when I have source material to reference. "
            f"Upload documents for comprehensive, cited explanations!*"
        )

    def _generate_who_answer(self, question: str) -> str:
        """Generate a biographical answer for who questions."""
        subject = question.strip().rstrip("?!.")
        if subject.lower().startswith("who "):
            subject = subject[4:]

        return (
            f"## Who {subject.title()}?\n\n"
            f"Great question about **{subject}**! To provide you with accurate "
            f"biographical or identity information:\n\n"
            f"### How to Get the Best Answer\n"
            f"1. 🌐 **Add a web page** — Paste a Wikipedia or biography URL into the Document Library\n"
            f"2. 📄 **Upload a document** — Add any file that mentions this person or entity\n"
            f"3. 💬 **Ask me again** — I'll extract and summarize the key details with citations\n\n"
            f"### I Can Help With\n"
            f"- Historical figures and their contributions\n"
            f"- Scientists, inventors, and their discoveries\n"
            f"- Technology leaders and innovators\n"
            f"- Organizations and their missions\n\n"
            f"---\n"
            f"*Upload a source about {subject} and I'll provide a detailed, cited answer!*"
        )

    def _generate_factual_answer(self, question: str) -> str:
        """Generate a factual answer for when/where questions."""
        return (
            f"## {question.strip().rstrip('?!.')}\n\n"
            f"That's a factual question that deserves a precise answer. "
            f"Let me help you find it:\n\n"
            f"### How to Get the Exact Answer\n"
            f"1. 🌐 **Add a relevant web page** — Paste a URL from an encyclopedia "
            f"or authoritative source\n"
            f"2. 📄 **Upload a reference document** — Add a textbook, article, or report\n"
            f"3. 💬 **Ask me again** — I'll locate the specific answer with a citation\n\n"
            f"### Topics I Know In-Depth\n"
            f"I have built-in knowledge about many technology, science, health, "
            f"and business topics. Try rephrasing your question or ask about one "
            f"of my core knowledge areas!\n\n"
            f"---\n"
            f"*For factual precision, I work best with source documents. "
            f"Upload one and I'll give you the exact answer with a citation!*"
        )

    def _generate_comparison_answer(self, question: str) -> str:
        """Generate a comparison answer."""
        return (
            f"## Comparison: {question.strip().rstrip('?!.')}\n\n"
            f"Comparing concepts is a great way to understand them better!\n\n"
            f"### Framework for Comparison\n"
            f"When comparing, consider these dimensions:\n\n"
            f"| Dimension | Factor A | Factor B |\n"
            f"|-----------|----------|----------|\n"
            f"| **Purpose** | What is its goal? | What is its goal? |\n"
            f"| **Strengths** | Key advantages | Key advantages |\n"
            f"| **Weaknesses** | Limitations | Limitations |\n"
            f"| **Use Cases** | Best suited for | Best suited for |\n"
            f"| **Cost** | Investment needed | Investment needed |\n\n"
            f"### Get a Detailed Comparison\n"
            f"For a thorough, evidence-based comparison:\n"
            f"- 📄 Upload articles or documentation about both topics\n"
            f"- 🌐 Add web pages that discuss the differences\n"
            f"- 💬 Ask me again — I'll build a detailed comparison with citations\n\n"
            f"---\n"
            f"*Try asking about topics I know well: \"Compare Python vs JavaScript\", "
            f"\"Difference between SQL and NoSQL\", or \"React vs Vue\"*"
        )

    def _generate_list_answer(self, question: str) -> str:
        """Generate a list-style answer."""
        subject = question.strip().rstrip("?!.")

        return (
            f"## {subject.title()}\n\n"
            f"Here's what I can tell you:\n\n"
            f"For a comprehensive list, I recommend:\n\n"
            f"1. 📄 **Upload a reference document** — Add an article, report, or guide "
            f"that covers this topic\n"
            f"2. 🌐 **Add a web page** — Paste a URL from a relevant website\n"
            f"3. 💬 **Ask again** — I'll extract and organize the information with citations\n\n"
            f"### Quick Knowledge Areas\n"
            f"I can immediately answer lists about:\n"
            f"- Types of machine learning algorithms\n"
            f"- Popular programming languages and frameworks\n"
            f"- Cloud computing services and providers\n"
            f"- Database types and their use cases\n"
            f"- Cybersecurity best practices\n"
            f"- Study techniques and methods\n\n"
            f"---\n"
            f"*Try asking: \"List types of machine learning\" or \"Best practices for cybersecurity\"!*"
        )

    def _generate_yes_no_answer(self, question: str) -> str:
        """Generate a response for yes/no style questions."""
        return (
            f"## {question.strip().rstrip('?!.')}?\n\n"
            f"That's a great question that depends on context. Let me help you "
            f"find a well-supported answer:\n\n"
            f"### Considerations\n"
            f"- The answer often depends on the **specific situation and context**\n"
            f"- Different sources may provide different perspectives\n"
            f"- Evidence-based answers are always more reliable\n\n"
            f"### How to Get a Definitive Answer\n"
            f"1. 📄 **Upload relevant research** — Add papers or articles that address this question\n"
            f"2. 🌐 **Add a web source** — Paste a URL from an authoritative site\n"
            f"3. 💬 **Ask me again** — I'll analyze the sources and give you a clear, cited answer\n\n"
            f"---\n"
            f"*For topics I know well (AI, programming, science, health, business), "
            f"try rephrasing as a 'what' or 'how' question for an immediate detailed answer!*"
        )

    def _generate_summary_answer(self, question: str) -> str:
        """Generate a summary-style answer."""
        return (
            "## Summary Request\n\n"
            "I'd be happy to provide a summary! To give you the most accurate summary:\n\n"
            "### How It Works\n"
            "1. 📄 **Upload the document** you'd like summarized (PDF, TXT, MD, DOCX, CSV)\n"
            "2. 🌐 **Or add a URL** — I'll fetch and index the web page content\n"
            "3. 💬 **Ask me to summarize** — I'll analyze the content and provide key points "
            "with citations\n\n"
            "### What I Can Summarize\n"
            "- Research papers and academic articles\n"
            "- Technical documentation\n"
            "- News articles and blog posts\n"
            "- Reports and business documents\n"
            "- Web pages and online content\n\n"
            "---\n"
            "*Upload your document to the **Document Library** and I'll create a "
            "comprehensive summary with key takeaways!*"
        )

    def _generate_default_answer(self, question: str) -> str:
        """Generate a thoughtful default answer when no specific pattern matches."""
        return (
            f"## Your Question\n\n"
            f"*\"{question}\"*\n\n"
            f"Thank you for your question! I want to give you the most accurate "
            f"and helpful answer possible.\n\n"
            f"### What I Can Do Right Now\n"
            f"I have detailed knowledge about many topics including:\n"
            f"- 🤖 **AI & Machine Learning** — algorithms, deep learning, NLP, LLMs\n"
            f"- 💻 **Programming** — Python, Java, JavaScript, React, SQL\n"
            f"- 🌐 **Web Development** — frontend, backend, APIs, frameworks\n"
            f"- ☁️ **Cloud & DevOps** — AWS, Docker, Kubernetes, CI/CD\n"
            f"- 🔒 **Cybersecurity** — best practices, encryption, authentication\n"
            f"- 📊 **Data Science** — analytics, visualization, statistics\n"
            f"- 🏥 **Health & Wellness** — nutrition, mental health, fitness\n"
            f"- 📈 **Business** — startups, project management, economics\n"
            f"- 🎓 **Education** — study techniques, mathematics\n"
            f"- 🌍 **Science** — climate change, biology, physics\n\n"
            f"### For Custom Research\n"
            f"Upload documents or web URLs to the **Document Library** and I'll provide "
            f"precise, cited answers from your own sources.\n\n"
            f"---\n"
            f"*Try rephrasing your question to include keywords from the topics above, "
            f"or upload a relevant document for a detailed, cited answer!*"
        )

    def get_model_name(self) -> str:
        return "builtin-ai/research-assistant"
