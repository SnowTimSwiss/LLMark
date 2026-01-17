
import base64
import json
import time
from datetime import datetime
from github import Github, GithubException

LLMARK_REPO_NAME = "SnowTimSwiss/LLMark-Site"
BENCHMARK_PATH_PREFIX = "data/benchmarks/"

class ContributionManager:
    """
    Manages the contribution of benchmark results to the central repository.
    """

    def upload_authenticated(self, token: str, benchmark_data: dict) -> str:
        """
        Uploads data using the user's personal access token.
        
        Process:
        1. Authenticate with GitHub.
        2. Fork the target repo (if not already forked).
        3. Create a new branch.
        4. Create a new file with the benchmark data.
        5. Create a Pull Request to the main repo.
        
        Returns:
            str: URL of the created Pull Request.
        """
        try:
            g = Github(token)
            user = g.get_user()
            target_repo = g.get_repo(LLMARK_REPO_NAME)
            
            # 1. Fork the repo
            my_fork = target_repo.create_fork()
            
            # Wait a moment for fork to be ready (Github API can be async)
            # In a real app we might retry, but a sleep helps
            time.sleep(2) 
            
            # 2. Create a branch
            # We base it on the forked repo's default branch (usually main or master)
            default_branch = my_fork.get_branch(my_fork.default_branch)
            branch_name = f"submission-{int(time.time())}"
            
            my_fork.create_git_ref(ref=f"refs/heads/{branch_name}", sha=default_branch.commit.sha)
            
            # 3. Create the file content
            # Filename: timestamp_modelname.json
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_model_name = benchmark_data.get("model", "unknown").replace(":", "-").replace("/", "-")
            file_name = f"{timestamp_str}_{safe_model_name}.json"
            file_path = f"{BENCHMARK_PATH_PREFIX}{file_name}"
            
            json_content = json.dumps(benchmark_data, indent=2, ensure_ascii=False)
            
            my_fork.create_file(
                path=file_path,
                message=f"Add result for {benchmark_data.get('model')}",
                content=json_content,
                branch=branch_name
            )
            
            # 4. Create Pull Request
            # head needs to be "username:branch_name"
            head = f"{user.login}:{branch_name}"
            
            pr = target_repo.create_pull(
                title=f"Benchmark Submission: {benchmark_data.get('model')}",
                body="Automated submission from LLMark Desktop App.",
                head=head,
                base=target_repo.default_branch
            )
            
            return pr.html_url

        except GithubException as e:
            # Re-raise with a cleaner error if possible, or just let it bubble
            raise Exception(f"GitHub Error: {e.data.get('message', str(e))}")
        except Exception as e:
            raise e

    def upload_anonymous(self, benchmark_data: dict):
        """
        Placeholder for anonymous upload logic.
        """
        raise NotImplementedError("Anonymous upload is not yet supported.")
