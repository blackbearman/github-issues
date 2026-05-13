import re
import os
import sys
import json

import requests

def fetch_issue_list(owner, repo, list_dir, token=None):
    issues = []
    i = 0
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=all"
    headers = {"Accept": "application/vnd.github.full+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    r = requests.get(url, headers=headers)
    while r.status_code == 200:
        data = r.json()
        with open(list_dir + f"issues{i}.json", "w") as f:
            json.dump(data, f)
        
        issues += [a["url"] for a in data if not 'pull_request' in a]
        if 'next' in r.links:
            next_url = r.links['next']['url']
            print(f"Next page URL: {next_url}")
            r = requests.get(next_url)
            i+=1
        else:
            break

    return issues

def fetch_issue_comments(issue_url, comments_dir, token=None):
    i = 0
    id = issue_url.split('/')[-1]
    url = f"{issue_url}/comments"
    headers = {"Accept": "application/vnd.github.full+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    r = requests.get(url, headers=headers)
    while r.status_code == 200:
        data = r.json()
        with open(comments_dir + f"issue{id}-c{i}.json", "w") as f:
            json.dump(data, f)
        
        if 'next' in r.links:
            next_url = r.links['next']['url']
            print(f"Next page URL: {next_url}")
            r = requests.get(next_url)
            i+=1
        else:
            break

    return i

if __name__ == "__main__":

    output_dir = 'output/'

    if len(sys.argv) < 3:
        print("Usage: python3 load.py <owner> <repo> [load] [convert] [github_token]")
        print("Example: python3 load.py blackbearman github-issues False True")
    else:
        owner = sys.argv[1]
        repo = sys.argv[2]
        load = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else False
        convert = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
        token = sys.argv[5] if len(sys.argv) > 5 else None
    
    lists_dir = output_dir + f'{repo}/lists/'
    comments_dir = output_dir + f'{repo}/comments/'

    if load:
        print(f"Load issues from {owner}/{repo}")
        issue_count = 0
        os.makedirs(lists_dir, exist_ok=True)
        issues = fetch_issue_list(owner, repo, lists_dir, token)

        issue_count = len(issues)
        print(issues)
        print(str(issue_count) + " issues found")

        os.makedirs(comments_dir, exist_ok=True)
        pages = 0
        for issue in issues:
            pages += fetch_issue_comments(issue, comments_dir, token)

        print(str(pages) + " pages loaded")

    if convert:
        print(f"Convert issues from {owner}/{repo} to Markdown")
        rows = []
        lists = [f for f in sorted(os.listdir(lists_dir)) if os.path.isfile(lists_dir + f)]
        comments = [f for f in sorted(os.listdir(comments_dir)) if os.path.isfile(comments_dir + f)]
        for l in lists:
            data = []
            with open(lists_dir + l, "r") as f:
                data = json.load(f)
            for s in data:
                # check issue or pull request
                if not "pull_request" in s:
                    rows.append(f"# {s['number']}  {s['title']}\n")
                    rows.append(f"*{s['user']['login']} created at {s['created_at']}*\n\n")
                    body = s["body"]
                    if body:
                        rows.append(f"{body}\n\n")

                    # load comments
                    i = 0
                    cname = f"issue{s['number']}-c{i}.json"
                    while cname in comments:
                        comment = []
                        with open(comments_dir + cname, "r") as f:
                            comment = json.load(f)
                        for c in comment:
                            rows.append(f"*{c['user']['login']} commented at {c['created_at']}*\n\n")
                            body = c["body"]
                            if body:
                                rows.append(f"{body}\n\n")
                        i += 1
                        cname = f"issue{s['number']}-c{i}.json"
                    if s['state'] == "closed":
                        rows.append(f"*{s['closed_by']['login']} closed at {s['closed_at']}*\n\n")

        with open(output_dir + f"{repo}/issues.md", "w") as f:
            f.writelines(rows)
