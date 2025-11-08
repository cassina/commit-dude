class CommitDude < Formula
  include Language::Python::Virtualenv

  desc "CLI that generates Conventional Commits from git diffs using LangChain + OpenAI"
  homepage "https://github.com/yourusername/commit-dude"
  url "https://files.pythonhosted.org/packages/source/c/commit-dude/commit-dude-0.1.0.tar.gz"
  sha256 "YOUR_SHA256_HASH_HERE"
  license "MIT"

  depends_on "python@3.13"

  resource "langchain" do
    url "https://files.pythonhosted.org/packages/source/l/langchain/langchain-0.3.20.tar.gz"
    sha256 "LANGCHAIN_SHA256"
  end

  resource "langchain-openai" do
    url "https://files.pythonhosted.org/packages/source/l/langchain-openai/langchain_openai-0.2.15.tar.gz"
    sha256 "LANGCHAIN_OPENAI_SHA256"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.8.tar.gz"
    sha256 "CLICK_SHA256"
  end

  resource "pyperclip" do
    url "https://files.pythonhosted.org/packages/source/p/pyperclip/pyperclip-1.9.0.tar.gz"
    sha256 "PYPERCLIP_SHA256"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/source/p/python-dotenv/python-dotenv-1.0.1.tar.gz"
    sha256 "PYTHON_DOTENV_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "commit-dude", shell_output("#{bin}/commit-dude --help")
  end
end