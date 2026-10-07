class Depgraph < Formula
  desc "Explainable dependency graphs for Rust, Go, TypeScript, and JavaScript"
  homepage "https://github.com/TamaT-LLC/depgraph-cli"
  license any_of: ["MIT", "Apache-2.0"]

  depends_on "node@24"

  if OS.mac?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.2/depgraph-0.6.2-aarch64-apple-darwin.tar.gz"
    sha256 "30a4e27db33c12f9dae837f34e59755a49ebf631803e8a8abb003c8ba5033f58"
  elsif Hardware::CPU.arm?
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.2/depgraph-0.6.2-aarch64-unknown-linux-gnu.tar.gz"
    sha256 "9e3d1028c91645e7fc74c7a1cfd4f661bcb785e669ad14ed2d2d1558dd8c1d80"
  else
    url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.2/depgraph-0.6.2-x86_64-unknown-linux-gnu.tar.gz"
    sha256 "dd4c9afe63d22988b1dbfa3a0676c6f6c7b11f168f6765eda133ca4c57ddc712"
  end

  on_macos do
    depends_on arch: :arm64
  end

  # Homebrew must not rewrite Node shebangs in checksum-verified release artifacts.
  skip_clean "libexec"

  def install
    # Supply prefix metadata so Homebrew does not move the verified package licenses.
    cp ["LICENSE-APACHE", "LICENSE-MIT"], prefix
    # Packaged workers verify the entire release tree. Preserve every byte and path.
    libexec.install Dir["*"]
    %w[depgraph depgraph-mcp].each do |name|
      (bin/name).write_env_script libexec/"bin"/name, PATH: "#{formula_opt_bin("node@24")}:$PATH"
    end
  end

  def caveats
    <<~EOS
      Go and Rust analysis use your project's existing toolchains and offline dependencies.
      MCP/compiler-precise analysis also requires the matching verified compiler pack;
      see https://github.com/TamaT-LLC/depgraph-cli#readme for setup.
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/depgraph --version")
    (testpath/"package.json").write('{"name":"brew-fixture","version":"1.0.0","type":"module"}')
    (testpath/"tsconfig.json").write('{"compilerOptions":{"strict":true},"include":["*.ts"]}')
    (testpath/"index.ts").write("export const value: number = 42;\n")
    store = testpath/"graph.sqlite"
    scan = JSON.parse(shell_output("#{bin}/depgraph --store #{store} scan #{testpath} --json"))
    assert_equal "completed", scan.fetch("status")
    assert_operator scan.dig("coverage", "files_analyzed"), :>, 0
    result = JSON.parse(shell_output("#{bin}/depgraph --store #{store} doctor --json"))
    assert_equal "verified", result.dig("release", "core_integrity")
    assert_equal "completed", result.dig("latest_attempt", "status")
    assert_equal %w[go rust web], result.fetch("workers").map { |worker| worker.fetch("adapter") }.sort
    result.fetch("workers").each { |worker| assert_equal "verified", worker.fetch("integrity") }
  end
end
