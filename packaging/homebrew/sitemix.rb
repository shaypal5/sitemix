class Sitemix < Formula
  include Language::Python::Virtualenv

  desc "LLM-oriented webpage/site dump CLI powered by trafilatura"
  homepage "https://github.com/<org>/sitemix"
  url "https://github.com/<org>/sitemix/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_TARBALL_SHA256"
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/sitemix", "--help"
  end
end
