class Depgraph < Formula
  desc "Explainable dependency graphs for Rust, Go, TypeScript, and JavaScript"
  homepage "https://github.com/TamaT-LLC/depgraph-cli"
  license any_of: ["MIT", "Apache-2.0"]

  depends_on "node@24"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.1/depgraph-0.6.1-aarch64-apple-darwin.tar.gz"
      sha256 "8790be64c7c582490ecb73a0b0d9d501a1eb7cdaee111e8e1e2f234f1ddd52be"
    else
      url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.1/depgraph-0.6.1-x86_64-apple-darwin.tar.gz"
      sha256 "6f8d57d05f165e1090955b16a93c0edafb001b1c366c3a1e5a3ab7f28340b665"
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.1/depgraph-0.6.1-aarch64-unknown-linux-gnu.tar.gz"
      sha256 "584a9d86be5005d848d01c4803b07dd73fe7ecd46cf21fd7f6b6bc191c47e211"
    else
      url "https://github.com/TamaT-LLC/depgraph-cli/releases/download/v0.6.1/depgraph-0.6.1-x86_64-unknown-linux-gnu.tar.gz"
      sha256 "d77b3f0232199337932478a25994edd49cae135e86f5c8a130d3f1af770a40a6"
    end
  end

  def install
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
    scan_text, scan_status = Open3.capture2("#{bin}/depgraph", "--store", store.to_s, "scan", testpath.to_s, "--json")
    ohai scan_text
    doctor_text, = Open3.capture2("#{bin}/depgraph", "--store", store.to_s, "doctor", "--json")
    ohai doctor_text
    assert_equal 0, scan_status.exitstatus
    scan = JSON.parse(scan_text)
    assert_equal "completed", scan.fetch("status")
    assert_operator scan.dig("coverage", "files_analyzed"), :>, 0
    result = JSON.parse(shell_output("#{bin}/depgraph --store #{store} doctor --json"))
    assert_equal "verified", result.dig("release", "core_integrity")
    assert_equal "completed", result.dig("latest_attempt", "status")
    assert_equal %w[go rust web], result.fetch("workers").map { |worker| worker.fetch("adapter") }.sort
    result.fetch("workers").each { |worker| assert_equal "verified", worker.fetch("integrity") }
  end
end
